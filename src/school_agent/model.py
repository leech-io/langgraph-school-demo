"""LangChain adapter for OpenAI-compatible DashScope endpoints."""
import json
import re
import os
from urllib.parse import urlsplit
from openai import DefaultHttpxClient, DefaultAsyncHttpxClient
from dataclasses import asdict
from typing import Literal
from pydantic import BaseModel, Field, StrictStr, model_validator
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from .prompts import PLAN_PROMPT, SUMMARY_PROMPT
from .config import redact

class ModelFailure(RuntimeError): pass

class ChartSpec(BaseModel):
    kind: Literal['bar','line','pie']
    x: StrictStr
    y: StrictStr
    title: str='成绩统计'

class QueryPlan(BaseModel):
    queries: list[StrictStr] = Field(max_length=10)
    chart: ChartSpec | None=None
    refusal: StrictStr | None=None
    @model_validator(mode='after')
    def check_queries(self):
        if not self.queries and not self.refusal: raise ValueError('计划没有SQL或拒绝原因')
        if self.refusal and self.queries: raise ValueError('拒绝时不应执行查询')
        if any(not q.strip() for q in self.queries): raise ValueError('SQL不能为空')
        return self

def clean_text(text):
    if not isinstance(text,str): raise ValueError('模型输出必须是文本')
    return re.sub(r'<think\b[^>]*>.*?</think\s*>','',text,flags=re.S|re.I).strip()

def parse_plan(text):
    text=clean_text(text)
    if text.startswith('```'):
        match=re.fullmatch(r'```(?:json)?\s*(.*?)\s*```',text,flags=re.S)
        if not match: raise ValueError('不完整JSON代码块')
        text=match.group(1)
    return QueryPlan.model_validate(json.loads(text))

class SchoolModel:
    def __init__(self,settings):
        self.settings=settings
        if not settings.model_api_key: raise ModelFailure('缺少MODEL_API_KEY，请在本机.env填写')
        # Choose the existing HTTP proxy explicitly; do not implicitly load ALL_PROXY SOCKS.
        proxy=next((os.environ[k] for k in ('HTTPS_PROXY','https_proxy','HTTP_PROXY','http_proxy')
                    if os.environ.get(k) and urlsplit(os.environ[k]).scheme in ('http','https')),None)
        self.llm=ChatOpenAI(http_client=DefaultHttpxClient(proxy=proxy,trust_env=False),
            http_async_client=DefaultAsyncHttpxClient(proxy=proxy,trust_env=False),model=settings.model_name,api_key=settings.model_api_key,
            base_url=settings.model_base_url,temperature=0,timeout=60,max_retries=0,http_socket_options=(),
            max_tokens=4096,extra_body={'enable_thinking':False})

    def plan(self,question,schema,error=''):
        messages=[SystemMessage(content=PLAN_PROMPT.replace('{schema}',schema)),HumanMessage(content=question)]
        if error: messages.append(HumanMessage(content='上次计划未通过，请重新生成完整JSON计划。错误：'+error))
        try:
            response=self.llm.bind(response_format={'type':'json_object'}).invoke(messages)
        except Exception as exc:
            raise ModelFailure('模型请求失败：'+redact(str(exc),self.settings)[:350]) from None
        return parse_plan(response.content)

    def summarize(self,question,results):
        payload=json.dumps([asdict(r) for r in results],ensure_ascii=False,default=str)
        try:
            response=self.llm.invoke([SystemMessage(content=SUMMARY_PROMPT),HumanMessage(content=question+'\n本次查询结果：\n'+payload)])
            return clean_text(response.content)
        except Exception as exc:
            raise ModelFailure('答案汇总失败：'+redact(str(exc),self.settings)[:350]) from None

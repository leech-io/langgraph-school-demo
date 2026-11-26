"""Explicit LangGraph orchestration: bounded, observable, read-only."""
from time import perf_counter
from langgraph.graph import StateGraph, START, END
from .state import AgentState
from .model import QueryPlan, ModelFailure
from .sql_guard import validate_sql, UnsafeQuery, InvalidQuery
from .db import DatabaseFailure, QueryFailure
from .config import redact


def build_graph(settings,db,model):
    def traced(title,fn):
        def wrapper(state):
            started=perf_counter();out=fn(state)
            detail=out.pop('_detail','完成')
            out['trace']=state.get('trace',[])+[{'node':title,'seconds':round(perf_counter()-started,3),'detail':detail}]
            return out
        return wrapper

    def fatal(message):
        message=redact(message,settings)
        return {'errors':[message],'last_error':message,'route':'stop','_detail':message}

    def retry_error(state,message):
        message=redact(message,settings)
        if state.get('repair_count',0)>=settings.max_repairs:
            return fatal('已达到修正上限：'+message)
        return {'last_error':message,'route':'repair','_detail':message}

    def prepare(state):
        initial={'results':[],'errors':[],'repair_count':0,'queries':[],'trace':[],'chart':None,'last_error':'','answer':''}
        question=state.get('question','').strip()
        if not question or len(question)>4000:
            return {**initial,**fatal('请输入1至4000字的完整成绩查询问题')}
        return {**initial,'question':question,'schema':db.schema_text,'route':'plan'}

    def generate(state):
        try:
            plan=model.plan(state['question'],state['schema'],state.get('last_error',''))
            if not isinstance(plan,QueryPlan): plan=QueryPlan.model_validate(plan)
            if len(plan.queries)>settings.max_queries: raise ValueError('查询数量超过上限')
            if plan.refusal: return fatal(plan.refusal)
            return {'queries':plan.queries,'chart':plan.chart.model_dump() if plan.chart else None,'route':'validate',
                    '_detail':f'生成{len(plan.queries)}条查询'}
        except ModelFailure as exc: return fatal(str(exc))
        except (ValueError,TypeError) as exc: return retry_error(state,str(exc))

    def validate(state):
        try:
            queries=[validate_sql(q,db.columns).sql for q in state['queries']]
            return {'queries':queries,'route':'execute','_detail':'只读SQL与字段校验通过'}
        except InvalidQuery as exc: return retry_error(state,str(exc))
        except UnsafeQuery as exc: return fatal('查询已拒绝：'+str(exc))

    def execute(state):
        results=[]
        try:
            for sql in state['queries']: results.append(db.query(sql))
            return {'results':results,'route':'finish','last_error':'','_detail':f'执行{len(results)}条查询，返回{sum(len(r.rows) for r in results)}行'}
        except QueryFailure as exc:
            # Preserve partial evidence, but do not automatically re-execute successful queries.
            if results: return {'results':results,**fatal('部分查询失败：'+str(exc))}
            return retry_error(state,str(exc))
        except (DatabaseFailure,UnsafeQuery) as exc:
            return {'results':results,**fatal(('部分查询失败：' if results else '')+str(exc))}

    def repair(state): return {'repair_count':state.get('repair_count',0)+1,'route':'plan','_detail':'准备重新生成并重新校验'}

    def finish(state):
        if state.get('errors'):
            prefix='部分查询已完成，以下结果不完整。\n\n' if state.get('results') else ''
            return {'answer':prefix+state['errors'][0],'_detail':'未完成；请查看原因'}
        results=state.get('results',[])
        if not results or all(not r.rows for r in results):
            return {'answer':'没有找到符合条件的成绩记录。','_detail':'无数据，未生成推测答案'}
        try:
            answer=model.summarize(state['question'],results)
            if any(r.truncated for r in results): answer+='\n\n⚠️ 查询结果已截断，仅展示前200行；明细不代表完整数据。'
            return {'answer':answer,'_detail':'基于本次实时查询结果生成'}
        except ModelFailure as exc:
            return {'errors':[str(exc)],'answer':str(exc)+'。SQL查询结果仍可在表格中查看。','_detail':'汇总失败，保留真实结果'}

    graph=StateGraph(AgentState)
    for name,title,fn in [('prepare','输入检查',prepare),('plan','生成SQL',generate),('validate','SQL校验',validate),
                          ('execute','查询MySQL',execute),('repair','错误修正',repair),('finish','汇总答案',finish)]:
        graph.add_node(name,traced(title,fn))
    graph.add_edge(START,'prepare')
    graph.add_conditional_edges('prepare',lambda s:s['route'],{'plan':'plan','stop':'finish'})
    graph.add_conditional_edges('plan',lambda s:s['route'],{'validate':'validate','repair':'repair','stop':'finish'})
    graph.add_conditional_edges('validate',lambda s:s['route'],{'execute':'execute','repair':'repair','stop':'finish'})
    graph.add_conditional_edges('execute',lambda s:s['route'],{'finish':'finish','repair':'repair','stop':'finish'})
    graph.add_edge('repair','plan');graph.add_edge('finish',END)
    return graph.compile()

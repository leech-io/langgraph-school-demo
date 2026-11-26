"""Run: uv run streamlit run app.py"""
from dataclasses import asdict
import pandas as pd
import streamlit as st
from school_agent.config import Settings,redact
from school_agent.db import SchoolDatabase,DatabaseFailure
from school_agent.model import SchoolModel,ModelFailure,ChartSpec
from school_agent.graph import build_graph
from school_agent.charts import render_chart,ChartUnavailable

st.set_page_config(page_title='学生成绩 · LangGraph',page_icon='🎓',layout='wide')
st.title('🎓 学生成绩查询助手')
st.caption('LangGraph × LangChain · 实时查询本地 MySQL · 只读演示')
settings=Settings.load()

@st.cache_resource(show_spinner=False)
def connect(config): return SchoolDatabase(config)

with st.sidebar:
    st.header('查询工作台')
    st.caption('模型')
    st.code(settings.model_name,language=None)
    st.caption('数据源：school_demo.student_grades')
    st.info('每次提问独立处理。请在问题中写完整班级、学期或科目条件。')
    if st.button('清空对话',use_container_width=True):
        st.session_state.history=[]
        st.rerun()
    st.divider()
    st.caption('执行边界')
    st.write('只读查询 · 最多200行展示 · 单条5秒超时 · 最多2次修正')
    st.caption('数据流：必要表结构和查询结果会发送给配置的模型服务（每条最多200行，每次最多10条）。')
    with st.expander('项目文档'):
        st.write('README.md')
        st.write('docs/superpowers/specs/2026-11-26-school-query-design.md')
        st.write('docs/superpowers/plans/2026-11-26-school-query-demo.md')

try:
    db=connect(settings)
except DatabaseFailure as exc:
    st.error(str(exc))
    st.caption('请检查项目根目录.env和MySQL只读账号。')
    st.stop()

with st.expander('数据库已连接 · 查看真实表结构',expanded=False):
    st.code(db.schema_text,language=None)
if not settings.model_api_key: st.warning('缺少MODEL_API_KEY，请填写项目.env后刷新页面。')

if 'history' not in st.session_state: st.session_state.history=[]

def show_response(out,index):
    if out.get('errors'):st.warning('本次任务未完整完成，请查看下方执行步骤。')
    st.markdown(out.get('answer','没有返回答案。'))
    for i,result in enumerate(out.get('results',[])):
        with st.expander(f'查询 {i+1} · {len(result.rows)}行'+(' · 已截断' if result.truncated else ''),expanded=True):
            st.code(result.sql,language='sql')
            st.dataframe(pd.DataFrame(result.rows,columns=result.columns),hide_index=True,width='stretch')
            if result.truncated:st.warning('仅展示前200行，明细不代表完整数据。')
        if out.get('chart') and i==0:
            try: st.plotly_chart(render_chart(result,ChartSpec.model_validate(out['chart'])),width='stretch',key=f'chart-{index}-{i}')
            except (ChartUnavailable,ValueError) as exc: st.info(str(exc))
    if not out.get('results') and out.get('queries'):
        with st.expander('未执行成功的SQL'):
            for sql in out['queries']:st.code(sql,language='sql')
    with st.expander('LangGraph 执行步骤 / Trace'):
        st.dataframe(pd.DataFrame(out.get('trace',[])).rename(columns={'node':'节点','seconds':'耗时（秒）','detail':'结果'}),hide_index=True,width='stretch')
        st.caption(f"SQL修正次数：{out.get('repair_count',0)} / 2")

if not st.session_state.history:
    st.markdown('试着问一个成绩问题')
    st.write('• 学校有多少名学生？\n• 各科平均分是多少？请画柱状图。\n• 全校平均分最高的班级是哪个？并列都列出来。\n• 各科及格与不及格的成绩记录分别有多少？')

for index,item in enumerate(st.session_state.history):
    with st.chat_message('user'):st.write(item['question'])
    with st.chat_message('assistant'):show_response(item['output'],index)

question=st.chat_input('输入完整问题，例如：各科平均分是多少？请画柱状图。',disabled=not bool(settings.model_api_key),max_chars=4000)
if question:
    with st.chat_message('user'):st.write(question)
    with st.chat_message('assistant'):
        try:
            graph=build_graph(settings,db,SchoolModel(settings))
            out={}
            with st.status('正在查询…',expanded=True) as status:
                for state in graph.stream({'question':question},stream_mode='values'):
                    out=state
                    if state.get('trace'):
                        event=state['trace'][-1]
                        st.write(f"{event['node']} · {event['detail']} · {event['seconds']}s")
                status.update(label='查询结束' if not out.get('errors') else '查询未完整完成',state='complete' if not out.get('errors') else 'error',expanded=False)
        except Exception as exc:
            out={'answer':'执行失败：'+redact(str(exc),settings)[:350],'errors':['执行失败'],'results':[],'trace':[]}
        st.session_state.history.append({'question':question,'output':out})
        show_response(out,len(st.session_state.history)-1)

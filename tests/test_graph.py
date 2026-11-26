import pytest
from school_agent.graph import build_graph
from school_agent.config import Settings
from school_agent.db import QueryResult, DatabaseFailure

class DB:
    columns={'student_id','subject','score','class_name','semester'}
    schema_text='student_grades(student_id,subject,score,class_name,semester)'
    def __init__(self, error=None): self.calls=[];self.error=error
    def query(self, sql):
        self.calls.append(sql)
        if self.error: raise self.error
        return QueryResult(sql=sql,columns=['n'],rows=[{'n':60}],truncated=False)

class Model:
    def __init__(self, plans): self.plans=iter(plans);self.calls=0
    def plan(self, question, schema, error):
        self.calls+=1
        p=next(self.plans)
        if isinstance(p,Exception): raise p
        return p
    def summarize(self, question, results): return '学生人数为60人。'

def run(db,model,question='学生有多少人'):
    return build_graph(Settings(),db,model).invoke({'question':question})

def test_graph_answers_from_live_query():
    db=DB();out=run(db,Model([{'queries':['SELECT COUNT(DISTINCT student_id) AS n FROM student_grades']}]))
    assert out['results'][0].rows==[{'n':60}]
    assert out['answer']=='学生人数为60人。'
    assert [x['node'] for x in out['trace']]==['输入检查','生成SQL','SQL校验','查询MySQL','汇总答案']

def test_dangerous_plan_never_executes():
    db=DB();out=run(db,Model([{'queries':['DELETE FROM student_grades']}]))
    assert db.calls==[]
    assert out['errors'] and not out['results']

def test_syntax_repair_is_bounded():
    model=Model([ValueError('invalid JSON')]*3);out=run(DB(),model)
    assert model.calls==3 and out['repair_count']==2
    assert out['errors'] and not out['results']

def test_can_repair_syntax_and_query():
    model=Model([ValueError('bad JSON'),{'queries':['SELECT COUNT(*) AS n FROM student_grades']}])
    out=run(DB(),model)
    assert out['repair_count']==1 and out['results'][0].rows==[{'n':60}]

def test_authentication_error_does_not_retry():
    model=Model([{'queries':['SELECT COUNT(*) AS n FROM student_grades']}])
    out=run(DB(DatabaseFailure('数据库认证失败')),model)
    assert model.calls==1 and out['errors'] and '认证' in out['answer']

def test_empty_data_not_invented():
    db=DB()
    db.query=lambda sql: QueryResult(sql=sql,columns=['score'],rows=[],truncated=False)
    out=run(db,Model([{'queries':['SELECT score FROM student_grades WHERE student_id=\'missing\'']}]))
    assert '没有' in out['answer'] or '无' in out['answer']

def test_partial_error_cannot_be_complete_success():
    db=DB();n=0
    def query(sql):
        nonlocal n
        n+=1
        if n==2: raise DatabaseFailure('连接中断')
        return QueryResult(sql=sql,columns=['n'],rows=[{'n':60}],truncated=False)
    db.query=query
    out=run(db,Model([{'queries':['SELECT COUNT(*) AS n FROM student_grades','SELECT COUNT(DISTINCT student_id) AS n FROM student_grades']}]))
    assert len(out['results'])==1 and out['errors']
    assert '部分' in out['answer']

def test_limits_query_count():
    db=DB();out=run(db,Model([{'queries':['SELECT COUNT(*) FROM student_grades']*11}]*3))
    assert not db.calls and out['errors']

def test_empty_question_does_not_call_model():
    model=Model([]);out=run(DB(),model,'   ')
    assert model.calls==0 and out['errors']

def test_unclosed_sql_can_be_repaired_in_graph():
    model=Model([{'queries':["SELECT score FROM student_grades WHERE subject='math"]},
                 {'queries':['SELECT COUNT(*) AS n FROM student_grades']}])
    out=run(DB(),model)
    assert out['repair_count']==1 and out['results'][0].rows==[{'n':60}]

import pytest
from school_agent.sql_guard import validate_sql, UnsafeQuery

COLUMNS = {'id','student_id','student_name','class_name','subject','score','exam_date','semester','grade','created_at','updated_at'}

@pytest.mark.parametrize('sql', [
 'SELECT COUNT(*) AS n FROM student_grades',
 'SELECT subject, AVG(score) AS avg_score FROM student_grades GROUP BY subject',
 'WITH a AS (SELECT class_name, AVG(score) AS avg_score FROM student_grades GROUP BY class_name) SELECT class_name, avg_score FROM a WHERE avg_score=(SELECT MAX(avg_score) FROM a)',
 'SELECT student_id, DENSE_RANK() OVER (ORDER BY score DESC) AS r FROM student_grades',
])
def test_allows_readonly_queries(sql):
    assert validate_sql(sql, COLUMNS).sql

@pytest.mark.parametrize('sql', [
 'DELETE FROM student_grades', 'UPDATE student_grades SET score=100',
 'SELECT score FROM student_grades; DROP TABLE student_grades',
 'SELECT * FROM mysql.user', 'SELECT score FROM school_demo.student_grades',
 "SELECT score FROM student_grades INTO OUTFILE '/tmp/x'",
 'SELECT SLEEP(10) FROM student_grades', 'SELECT BENCHMARK(10000,1) FROM student_grades',
 "SELECT LOAD_FILE('/etc/passwd') FROM student_grades",
 'SELECT score FROM student_grades FOR UPDATE', 'SELECT unknown FROM student_grades',
 'SELECT @@version FROM student_grades', 'SELECT @x:=score FROM student_grades',
 'SELECT some_udf(score) FROM student_grades', 'SELECT score FROM student_grades a CROSS JOIN student_grades b',
 'SELECT * FROM student_grades', 'SELECT 1',
])
def test_rejects_unsafe_queries(sql):
    with pytest.raises(UnsafeQuery): validate_sql(sql, COLUMNS)

def test_logical_operators_are_not_mistaken_for_external_functions():
    sql="SELECT CASE WHEN score >= 60 AND score < 90 THEN '及格' ELSE '其他' END AS band FROM student_grades WHERE score<60 OR score>=90"
    assert validate_sql(sql,COLUMNS).sql

def test_nested_cte_does_not_authorize_outer_physical_table():
    sql='SELECT COUNT(*) AS total, (WITH hidden AS (SELECT score FROM student_grades) SELECT COUNT(*) FROM hidden) AS n FROM hidden'
    with pytest.raises(UnsafeQuery):validate_sql(sql,COLUMNS)

def test_unclosed_string_is_a_repairable_query_error():
    from school_agent.sql_guard import InvalidQuery
    with pytest.raises(InvalidQuery):validate_sql("SELECT score FROM student_grades WHERE subject='math",COLUMNS)

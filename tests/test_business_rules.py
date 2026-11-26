"""Hand-checked fixture verifies runtime preserves CTE scope, ties, and precision."""
import sqlite3
from school_agent.sql_guard import validate_sql

def test_tied_highest_average_preserves_all_classes_before_rounding():
    conn=sqlite3.connect(':memory:')
    conn.execute('CREATE TABLE student_grades(student_id TEXT,class_name TEXT,score REAL,semester TEXT)')
    conn.executemany('INSERT INTO student_grades VALUES(?,?,?,?)',[
      ('1','A',80,'S1'),('2','A',90,'S1'),('3','B',85,'S1'),('4','C',84.999,'S1')])
    sql='WITH c AS (SELECT class_name,AVG(score) AS raw_avg FROM student_grades GROUP BY class_name) SELECT class_name,ROUND(raw_avg,2) AS avg_score FROM c WHERE raw_avg=(SELECT MAX(raw_avg) FROM c) ORDER BY class_name'
    valid=validate_sql(sql,{'student_id','class_name','score','semester'})
    assert conn.execute(valid.sql).fetchall()==[('A',85.0),('B',85.0)]
    conn.close()

def test_distinct_students_and_semester_filter():
    conn=sqlite3.connect(':memory:')
    conn.execute('CREATE TABLE student_grades(student_id TEXT,score REAL,semester TEXT)')
    conn.executemany('INSERT INTO student_grades VALUES(?,?,?)',[('1',60,'S1'),('1',90,'S2'),('2',50,'S1')])
    sql=validate_sql('SELECT COUNT(*) AS records, COUNT(DISTINCT student_id) AS students FROM student_grades',{'student_id','score','semester'}).sql
    assert conn.execute(sql).fetchone()==(3,2)
    sql=validate_sql("SELECT AVG(score) AS avg_score FROM student_grades WHERE semester='S1'",{'student_id','score','semester'}).sql
    assert conn.execute(sql).fetchone()==(55.0,)
    conn.close()

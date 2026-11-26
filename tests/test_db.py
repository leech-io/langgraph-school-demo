from school_agent.db import collect_rows

def test_fetches_extra_row_to_report_truncation():
    class Result:
        def keys(self): return ['n']
        def fetchmany(self, n):
            assert n == 3
            return [(1,), (2,), (3,)]
    result = collect_rows(Result(), 'SELECT n', 2)
    assert result.rows == [{'n':1},{'n':2}]
    assert result.truncated is True

import os
import pytest

@pytest.mark.skipif(os.environ.get('RUN_MYSQL_TESTS')!='1',reason='requires local readonly MySQL')
def test_mysql_percent_literal_is_not_treated_as_driver_placeholder():
    from school_agent.config import Settings
    from school_agent.db import SchoolDatabase
    db=SchoolDatabase(Settings.load())
    try:
        assert db.query("SELECT '100%' AS label FROM student_grades LIMIT 1").rows==[{'label':'100%'}]
    finally:db.close()

@pytest.mark.skipif(os.environ.get('RUN_MYSQL_TESTS')!='1',reason='requires local readonly MySQL')
def test_mysql_real_detail_query_is_bounded_and_marked():
    from school_agent.config import Settings
    from school_agent.db import SchoolDatabase
    db=SchoolDatabase(Settings.load())
    try:
        result=db.query('SELECT id FROM student_grades ORDER BY id')
        assert len(result.rows)==200 and result.truncated
        small=db.query('SELECT id FROM student_grades ORDER BY id LIMIT 3')
        assert len(small.rows)==3 and not small.truncated
    finally:db.close()

@pytest.mark.skipif(os.environ.get('RUN_MYSQL_TESTS')!='1',reason='requires local readonly MySQL')
def test_mysql_colon_literal_is_not_a_bound_parameter():
    from school_agent.config import Settings
    from school_agent.db import SchoolDatabase
    db=SchoolDatabase(Settings.load())
    try:
        assert db.query("SELECT ':midterm' AS label FROM student_grades LIMIT 1").rows==[{'label':':midterm'}]
    finally:db.close()

def test_duplicate_columns_do_not_silently_overwrite_data():
    from school_agent.db import QueryFailure
    class Result:
        def keys(self):return ['n','n']
        def fetchmany(self,n):return [(60,600)]
    with pytest.raises(QueryFailure):collect_rows(Result(),'sql',200)

def test_readonly_grant_with_delegation_is_rejected():
    from school_agent.db import SchoolDatabase,DatabaseFailure
    class Connection:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def exec_driver_sql(self,sql):
            return [('GRANT SELECT ON `school_demo`.`student_grades` TO `reader`@`localhost` WITH GRANT OPTION',)]
    class Engine:
        def connect(self):return Connection()
    db=object.__new__(SchoolDatabase);db.engine=Engine()
    with pytest.raises(DatabaseFailure):db._verify_privileges()

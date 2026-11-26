"""Read-only MySQL access with bounded results and secret-safe failures."""
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
import re
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import DBAPIError, SQLAlchemyError
from sqlalchemy.engine import make_url
import sqlglot
from .config import Settings, redact
from .sql_guard import validate_sql

class DatabaseFailure(RuntimeError): pass
class QueryFailure(ValueError): pass

@dataclass
class QueryResult:
    sql: str
    columns: list[str]
    rows: list[dict]
    truncated: bool = False

def json_value(value):
    if isinstance(value,Decimal): return float(value)
    if isinstance(value,(date,datetime)): return value.isoformat()
    if isinstance(value,bytes): return '<二进制数据>'
    return value

def collect_rows(result, sql, max_rows):
    columns=list(result.keys())
    if len({c.casefold() for c in columns})!=len(columns):
        raise QueryFailure('查询结果列名重复，请给每个字段使用唯一别名')
    rows=result.fetchmany(max_rows+1)
    return QueryResult(sql,columns,[{k:json_value(v) for k,v in zip(columns,row)} for row in rows[:max_rows]],len(rows)>max_rows)

class SchoolDatabase:
    def __init__(self, settings: Settings):
        self.settings=settings
        if not settings.database_url: raise DatabaseFailure('缺少DATABASE_URL，请在本机.env配置')
        try:
            url=make_url(settings.database_url)
            if url.drivername!='mysql+pymysql' or url.database!='school_demo':
                raise DatabaseFailure('数据库连接必须使用mysql+pymysql并指向school_demo')
            self.engine=create_engine(url,connect_args={'connect_timeout':5,'read_timeout':7,'write_timeout':5},
                                      pool_pre_ping=True,hide_parameters=True,pool_recycle=300)
            self._verify_privileges()
            with self.engine.connect() as conn:
                fields=inspect(conn).get_columns('student_grades')
                if not fields: raise DatabaseFailure('未找到student_grades')
                self.columns={f['name'] for f in fields}
                self.schema_text='student_grades（学生成绩，模拟数据）\n'+'\n'.join(f"{f['name']}: {f['type']} {f.get('comment') or ''}" for f in fields)
        except DatabaseFailure: raise
        except Exception as exc: raise DatabaseFailure(self.safe_error(exc)) from None

    def safe_error(self, exc):
        code=exc.orig.args[0] if isinstance(exc,DBAPIError) and exc.orig.args else None
        if code in (1044,1045,1142): return '数据库认证或权限失败，请检查只读账号'
        if code in (2002,2003,2006,2013): return '数据库连接失败或中断，请确认MySQL服务和地址'
        if code in (3024,): return '查询超过5秒，已停止，请缩小范围'
        return '数据库操作失败：'+redact(str(exc),self.settings)[:350]

    def _verify_privileges(self):
        with self.engine.connect() as conn:
            grants=[row[0] for row in conn.exec_driver_sql('SHOW GRANTS')]
            for grant in grants:
                if 'WITH GRANT OPTION' in grant.upper():
                    raise DatabaseFailure('账号包含转授权能力，请使用不带GRANT OPTION的只读账号')
                match=re.fullmatch(r'GRANT (.+?) ON (.+?) TO .+',grant,flags=re.I)
                if not match: raise DatabaseFailure('存在角色或无法验证的授权，请使用独立SELECT账号')
                permissions,target=match.groups()
                if permissions.upper()=='USAGE': continue
                if permissions.upper()!='SELECT': raise DatabaseFailure('数据库账号拥有写入或管理权限，请改用只读账号')
                target=target.replace('`','')
                if target not in ('school_demo.student_grades','school_demo.*'):
                    raise DatabaseFailure('只读账号授权范围超出school_demo')
                if target=='school_demo.*':
                    tables={r[0] for r in conn.exec_driver_sql('SHOW TABLES')}
                    if tables!={'student_grades'}: raise DatabaseFailure('库级授权包含其他表，请将账号范围收窄到student_grades')

    def query(self, sql):
        validated=validate_sql(sql,self.columns)
        tree=sqlglot.parse_one(validated.sql,read='mysql')
        existing=tree.args.get('limit')
        cap=self.settings.max_rows+1
        if existing is None or int(existing.expression.this)>cap: tree=tree.limit(cap)
        bounded=tree.sql(dialect='mysql')
        try:
            with self.engine.connect() as conn:
                conn.exec_driver_sql('SET SESSION TRANSACTION READ ONLY')
                conn.exec_driver_sql(f'SET SESSION MAX_EXECUTION_TIME={self.settings.timeout_seconds*1000}')
                conn.rollback()
                try: return collect_rows(conn.exec_driver_sql(bounded,execution_options={'no_parameters':True}),bounded,self.settings.max_rows)
                finally: conn.rollback()
        except DBAPIError as exc:
            code=exc.orig.args[0] if exc.orig.args else None
            if code in (1054,1064,1055,1140): raise QueryFailure('SQL执行错误：'+redact(str(exc.orig),self.settings)[:250]) from None
            raise DatabaseFailure(self.safe_error(exc)) from None
        except SQLAlchemyError as exc: raise DatabaseFailure(self.safe_error(exc)) from None

    def close(self): self.engine.dispose()

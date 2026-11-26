"""Fail-closed SQL AST validation. Database SELECT privileges remain essential."""
from dataclasses import dataclass
import sqlglot
from sqlglot import exp
from sqlglot.optimizer.qualify import qualify
from sqlglot.errors import ParseError, OptimizeError, TokenError
from sqlglot.optimizer.scope import traverse_scope

class UnsafeQuery(ValueError): pass
class InvalidQuery(UnsafeQuery): pass

@dataclass(frozen=True)
class ValidatedQuery:
    sql: str

ALLOWED_FUNCTIONS = {
 'AND','OR','NOT','COUNT','SUM','AVG','MIN','MAX','ROUND','ABS','CEIL','CEILING','FLOOR','MOD',
 'COALESCE','IF','IFNULL','NULLIF','CASE','CAST','TRY_CAST','CONCAT','CONCAT_WS',
 'LOWER','UPPER','TRIM','LENGTH','CHAR_LENGTH','SUBSTRING','REPLACE','DATE','YEAR',
 'MONTH','DAY','DAYOFMONTH','DATE_FORMAT','DATE_ADD','DATE_SUB','DATEDIFF','TIMESTAMPDIFF',
 'CURRENT_DATE','CURRENT_TIMESTAMP','NOW','ROW_NUMBER','RANK','DENSE_RANK','LAG','LEAD',
 'FIRST_VALUE','LAST_VALUE','PERCENT_RANK','CUME_DIST','NTILE','EXTRACT',
}
FORBIDDEN_KEYS = {'into','lock','command','set','delete','update','insert','create','drop','alter',
                 'transaction','commit','rollback','grant','revoke','use','parameter','sessionparameter',
                 'propertyeq','assignment','join','hint','lateral','offset'}

def validate_sql(sql: str, columns: set[str]) -> ValidatedQuery:
    if not isinstance(sql,str) or not sql.strip(): raise InvalidQuery('SQL为空')
    if len(sql)>20000: raise UnsafeQuery('SQL超过长度限制')
    try: trees=sqlglot.parse(sql, read='mysql')
    except (ParseError,TokenError) as exc: raise InvalidQuery('SQL语法错误，请重新生成MySQL SELECT') from exc
    if len(trees)!=1 or trees[0] is None: raise UnsafeQuery('每项只允许一条查询')
    tree=trees[0]
    if not isinstance(tree,(exp.Select,exp.Union)): raise UnsafeQuery('仅允许SELECT或只读CTE')
    ctes={c.alias_or_name.lower() for c in tree.find_all(exp.CTE)}
    if 'student_grades' in ctes: raise UnsafeQuery('CTE不能覆盖真实表名')
    physical=[]
    for node in tree.walk():
        if node.key.lower() in FORBIDDEN_KEYS: raise UnsafeQuery('SQL包含禁止的操作或结构')
        if node.comments: node.comments=[]
        if isinstance(node,exp.Table):
            if node.db or node.catalog: raise UnsafeQuery('不允许跨库或显式指定数据库')
            if node.name.lower()=='student_grades': physical.append(node)
            elif node.name.lower() not in ctes: raise UnsafeQuery('只能读取student_grades')
        if isinstance(node,exp.Func):
            name=node.name.upper() if isinstance(node,exp.Anonymous) else node.sql_name().upper()
            if name not in ALLOWED_FUNCTIONS: raise UnsafeQuery('不允许的SQL函数：'+name)
        if isinstance(node,exp.Star) and not isinstance(node.parent,exp.Count):
            raise InvalidQuery('请明确列出需要查询的字段，不使用SELECT *')
    # Resolve every source in its own lexical scope. An inner CTE cannot
    # authorize an outer table merely because the names match.
    for scope in traverse_scope(tree):
        for _, source in scope.selected_sources.values():
            if isinstance(source,exp.Table) and (source.name.lower()!='student_grades' or source.db or source.catalog):
                raise UnsafeQuery('查询作用域包含未授权的物理表')
    if not physical: raise UnsafeQuery('查询必须读取student_grades')
    try:
        qualify(tree.copy(), dialect='mysql', schema={'student_grades':{c:'UNKNOWN' for c in columns}},
                validate_qualify_columns=True, quote_identifiers=False)
    except OptimizeError as exc: raise InvalidQuery('字段或别名不存在，请核对表结构：'+str(exc)[:180]) from exc
    except Exception as exc: raise InvalidQuery('无法验证SQL字段与作用域') from exc
    for limit in tree.find_all(exp.Limit):
        val=limit.expression
        if not isinstance(val,exp.Literal) or not val.is_int or int(val.this)<0:
            raise UnsafeQuery('LIMIT必须是非负整数')
    return ValidatedQuery(tree.sql(dialect='mysql'))

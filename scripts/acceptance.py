"""Live-model acceptance against independent reference SQL. Never writes to MySQL."""
import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from school_agent.config import Settings, ROOT, redact
from school_agent.db import SchoolDatabase
from school_agent.model import SchoolModel
from school_agent.graph import build_graph

CASES=json.loads((ROOT/'tests/acceptance_cases.json').read_text())

def comparable(rows):
    def norm(value):return round(value,2) if isinstance(value,(float,int)) else value
    return sorted([tuple((k,norm(v)) for k,v in sorted(r.items())) for r in rows],key=repr)

def main():
    settings=Settings.load();db=SchoolDatabase(settings)
    def check(case):
        name,question,reference=case
        expected=db.query(reference).rows
        try:
            out=build_graph(settings,db,SchoolModel(settings)).invoke({'question':question})
            actual=out['results'][0].rows if len(out.get('results',[]))==1 else None
            passed=not out.get('errors') and actual is not None and comparable(actual)==comparable(expected)
            return {'case':name,'passed':passed,'question':question,'reference_sql':reference,
                    'expected':expected,'actual':actual,'sql':out.get('queries',[]),'answer':out.get('answer',''),
                    'errors':out.get('errors',[]),'repair_count':out.get('repair_count',0)}
        except Exception as exc:
            return {'case':name,'passed':False,'question':question,'reference_sql':reference,'error':redact(str(exc),settings)}
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(check,CASES))
    finally:db.close()
    work=ROOT/'work';work.mkdir(exist_ok=True)
    (work/'live-acceptance.json').write_text(json.dumps(results,ensure_ascii=False,indent=2,default=str))
    passed=sum(r['passed'] for r in results)
    report=['# 真实模型与MySQL验收','',f'执行时间：{datetime.now().astimezone().isoformat()}',f'模型：{settings.model_name}',f'结果：{passed}/{len(results)}通过。','',
            '独立参考SQL与模型实际查询结果逐项比较；仅执行SELECT，没有写入或创建测试数据。模型随机性和实际数据变化会影响后续运行。','']
    for r in results:
        report.extend([f"## {'PASS' if r['passed'] else 'FAIL'}：{r['case']}",r['question'],'','基准SQL：','```sql',r['reference_sql'],'```',
                       '实际SQL：','```sql','\n'.join(r.get('sql',[])),'```',f"修正次数：{r.get('repair_count',0)}",f"错误：{r.get('errors',r.get('error',[]))}",''])
    (ROOT/'docs/acceptance-report.md').write_text('\n'.join(report))
    for r in results:print(('PASS' if r['passed'] else 'FAIL'),r['case'])
    print(f'真实模型验收：{passed}/{len(results)}；详情 docs/acceptance-report.md')
    return 0 if passed==len(results) else 1

if __name__=='__main__':raise SystemExit(main())

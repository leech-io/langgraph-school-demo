import pytest
from school_agent.charts import render_chart, ChartSpec, ChartUnavailable
from school_agent.db import QueryResult

@pytest.mark.parametrize('kind',['bar','line','pie'])
def test_chart_uses_query_labels_and_values(kind):
    result=QueryResult(sql='sql',columns=['subject','avg_score'],rows=[{'subject':'数学','avg_score':75.5},{'subject':'语文','avg_score':81}],truncated=False)
    fig=render_chart(result,ChartSpec(kind=kind,x='subject',y='avg_score',title='均分'))
    trace=fig.to_dict()['data'][0]
    if kind=='pie': assert list(trace['labels'])==['数学','语文'] and list(trace['values'])==[75.5,81]
    else: assert list(trace['x'])==['数学','语文'] and list(trace['y'])==[75.5,81]

@pytest.mark.parametrize('rows',[[],[{'s':'数学','n':-1}],[{'s':'数学','n':'n/a'}]])
def test_invalid_pie_data_rejected(rows):
    with pytest.raises(ChartUnavailable): render_chart(QueryResult(sql='sql',columns=['s','n'],rows=rows,truncated=False),ChartSpec(kind='pie',x='s',y='n'))

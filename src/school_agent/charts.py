"""Charts built exclusively from query rows, never model-generated values."""
import math
from numbers import Real
from decimal import Decimal
import plotly.graph_objects as go
from .model import ChartSpec

class ChartUnavailable(ValueError): pass

def render_chart(result,spec: ChartSpec):
    if not result.rows: raise ChartUnavailable('没有数据可绘图')
    if spec.x not in result.columns or spec.y not in result.columns: raise ChartUnavailable('图表字段不在查询结果中，已保留表格')
    labels=[];values=[]
    for row in result.rows:
        val=row.get(spec.y)
        if isinstance(val,bool) or not isinstance(val,(Real,Decimal)) or not math.isfinite(float(val)):
            raise ChartUnavailable('所选数值列包含空值或非数值，已保留表格')
        if row.get(spec.x) is None: raise ChartUnavailable('标签列包含空值，已保留表格')
        labels.append(str(row[spec.x]));values.append(float(val))
    if len(set(labels))!=len(labels): raise ChartUnavailable('标签重复，请先按图表维度聚合；已保留表格')
    if spec.kind=='pie':
        if min(values)<0 or sum(values)<=0: raise ChartUnavailable('饼图需要非负且总和大于零的数据')
        trace=go.Pie(labels=labels,values=values,hole=.35)
    elif spec.kind=='line': trace=go.Scatter(x=labels,y=values,mode='lines+markers')
    else: trace=go.Bar(x=labels,y=values,marker_color='#2563eb')
    fig=go.Figure(trace)
    fig.update_layout(title=spec.title,template='plotly_white',margin=dict(l=20,r=20,t=55,b=20),height=380)
    return fig

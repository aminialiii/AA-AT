"""Static research charts with ReportLab's standard LinePlot chart library."""
import csv,json,math,hashlib
from pathlib import Path
from reportlab.graphics.shapes import Drawing,String,Rect
from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics import renderSVG
from reportlab.lib.colors import HexColor
R=Path('E:/GPT/Inves/research/overnight-20261010');state=json.loads((R/'state.json').read_text());folder=Path(state['latestReportFolder']);source=folder/'equity_drawdown_data.csv'
rows=list(csv.DictReader(source.open(encoding='utf-8-sig')));symbols=['XAUUSD','EURUSD','GBPUSD','USDJPY','USDCHF','USDCAD','AUDUSD'];blue=HexColor('#2563eb');green=HexColor('#008859');gray=HexColor('#334155')
d=Drawing(1000,1230);d.add(Rect(0,0,1000,1230,fillColor=HexColor('#ffffff'),strokeColor=None));d.add(String(28,1197,'SIMULATED equity and drawdown by symbol',fontName='Helvetica-Bold',fontSize=20,fillColor=gray));d.add(String(28,1173,'Fixed 1R per closed trade. Blue: validation. Green: sealed holdout if released. Not real demo equity.',fontName='Helvetica',fontSize=11,fillColor=gray))
for n,symbol in enumerate(symbols):
 y=1005-n*150;d.add(String(30,y+128,symbol,fontName='Helvetica-Bold',fontSize=13,fillColor=gray))
 for col,field in enumerate(['equityR','drawdownR']):
  data=[];colors=[]
  for part,color in [('validation',blue),('sealed_holdout',green)]:
   series=[(0,0)]+[(float(r['closedSimulationIndex']),float(r[field])) for r in rows if r['symbol']==symbol and r['partition']==part]
   if len(series)>1:data.append(series);colors.append(color)
  x=75+col*490;lp=LinePlot();lp.x=x;lp.y=y+20;lp.width=395;lp.height=90;lp.data=data or [[(0,0),(1,0)]];lp.joinedLines=1;lp.lines.symbol=None
  values=[point[1] for series in lp.data for point in series];lo=min(0,min(values));hi=max(0,max(values));span=max(1,hi-lo);lp.yValueAxis.valueMin=lo-.05*span;lp.yValueAxis.valueMax=hi+.05*span
  raw_step=span/4;power=10**math.floor(math.log10(raw_step));fraction=raw_step/power;lp.yValueAxis.valueStep=power*(1 if fraction<=1 else 2 if fraction<=2 else 5 if fraction<=5 else 10)
  lp.xValueAxis.valueMin=0;lp.xValueAxis.valueMax=max(1,max(point[0] for series in lp.data for point in series));lp.xValueAxis.valueStep=max(1,round(lp.xValueAxis.valueMax/4));lp.xValueAxis.labels.fontSize=10;lp.yValueAxis.labels.fontSize=10
  for i,color in enumerate(colors):lp.lines[i].strokeColor=color;lp.lines[i].strokeWidth=1.2
  d.add(lp);d.add(String(x,y+116,'Equity (R)' if field=='equityR' else 'Drawdown (R)',fontName='Helvetica',fontSize=10,fillColor=gray));d.add(String(x+120,y,'Closed simulated trade index',fontName='Helvetica',fontSize=8,fillColor=gray))
svg=folder/'equity_drawdown.svg';renderSVG.drawToFile(d,str(svg));report=json.loads((folder/'report.json').read_text());report['charts']={'SVG':str(svg),'sourceCSV':str(source),'library':'ReportLab LinePlot','SHA256':hashlib.sha256(svg.read_bytes()).hexdigest(),'actualDemoEquity':False}
with (folder/'report_with_charts.json').open('x',encoding='utf-8') as f:json.dump(report,f,ensure_ascii=False,indent=2)
state['latestReportJSON']=str(folder/'report_with_charts.json');temp=R/'state.chart.tmp';temp.write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8');temp.replace(R/'state.json')
with (folder/'REPORT.md').open('a',encoding='utf-8') as f:f.write('\n## نمودار شبیه‌سازی\n\n![Equity and Drawdown](equity_drawdown.svg)\n\nموجودی و افت حساب واقعی نیست؛ مقیاس ثابت یک R برای هر معاملهٔ بسته‌شدهٔ شبیه‌سازی است.\n')
print(json.dumps({'stage':'charts','SVG':str(svg),'reportJSON':str(folder/'report_with_charts.json'),'curves':len(rows),'brokerMutations':0}))

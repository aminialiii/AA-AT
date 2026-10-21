"""Frozen M1/M5 research comparison, diagnostics and one sealed final evaluation.

All trades are simulations. This module cannot send broker orders.
"""
import sys,json,gzip,csv,math,statistics,importlib.util
from pathlib import Path
from datetime import datetime,timezone
import engine as e
spec=importlib.util.spec_from_file_location('overnight_m5',e.R/'m5/engine.py')
m5=importlib.util.module_from_spec(spec);spec.loader.exec_module(m5)
R=e.R
ENGINES={'M1':e,'M5':m5}

def generations():
 return [(tf,en,en.read(en.R/'state.json')) for tf,en in ENGINES.items()]

def all_groups():
 groups={}
 for tf,en,s in generations():groups.update(en.trade_rows())
 return groups

def selected_groups():
 st=e.read(R/'state.json');sel=e.read(st['combinedSelectionPath']);groups=all_groups()
 return sel,{c['symbol']:[x for x in groups.get((c['symbol'],c['model']['id']),[]) if x['partition']=='validation'] for c in sel['choices']}

def select():
 st=e.read(R/'state.json')
 if st.get('combinedSelectionPath'):print(json.dumps({'stage':'combined_select','alreadyCompleted':True}));return
 if st.get('holdoutOpened'):raise RuntimeError('selection_after_holdout_forbidden')
 sources=[];candidates=[]
 for tf,en,s in generations():
  selection=en.read(s['selectionPath']);proof=en.read(s['verificationPath'])
  if proof['violations']:raise RuntimeError('causality_required_'+tf)
  sources.append({'timeframe':tf,'selectionPath':s['selectionPath'],'selectionSHA256':en.digest(s['selectionPath']),'planPath':str(en.R/'plan.json'),'planSHA256':en.digest(en.R/'plan.json'),'verificationPath':s['verificationPath']})
  for c in selection['choices']:candidates.append({**c,'timeframe':tf,'barSeconds':60 if tf=='M1' else 300,'sourceSelectionPath':s['selectionPath'],'developmentScore':e.score(c['validation'])})
 choices=[]
 for name in e.read(R/'request.json')['symbols']:
  eligible=[c for c in candidates if c['symbol']==name]
  eligible.sort(key=lambda c:(c['provisionalGate'],c['developmentScore'],c['timeframe']=='M1'),reverse=True)
  choices.append(eligible[0])
 choices.sort(key=lambda c:(c['provisionalGate'],c['developmentScore']),reverse=True)
 data={'registeredUTC':e.utc(),'kind':'FROZEN_COMBINED_DEVELOPMENT_SELECTION','selectionRule':'Prefer registered provisional gate; otherwise same validation expectancy minus .15*DD/n score, minimum n50. Ties prefer M1. No final-test outcome used.','sources':sources,'choices':choices,'bestDevelopmentSymbol':choices[0]['symbol'],'registeredModelSymbolComparisons':448,'holdoutEvaluated':False,'adaptiveGenerationWarning':'M5 was prospectively registered after M1 development results; all 448 searches belong to the same selection process.','foldLimitation':'Positive walk-forward folds assess the prequential selection procedure, not stability of a fixed model selected retrospectively.','trainCoverageLimitation':'M1 initial July9 training day has partial FX coverage; M5 starts July10. Validation and final-test windows are identical.','primaryTest':'Only the preselected best development symbol is the primary final-test claim; other symbols remain descriptive. No reselection on final results.','strategyPromotionAllowed':False}
 p=e.save('frozen_combined_selection',data);e.finish('combined_select',p,combinedSelectionPath=p,nextStage='ticks')

def diagnostics():
 st=e.read(R/'state.json')
 if st.get('diagnosticsPath'):print(json.dumps({'stage':'diagnostics','alreadyCompleted':True}));return
 sel=e.read(st['combinedSelectionPath']);groups=all_groups();results=[]
 for c in sel['choices']:
  en=ENGINES[c['timeframe']];allrows=groups.get((c['symbol'],c['model']['id']),[]);train=[x for x in allrows if x['partition']=='train'];val=[x for x in allrows if x['partition']=='validation']
  median=statistics.median([x['signalATR'] for x in train]) if train else None
  diagnostics={}
  fields={'hour':lambda x:str(x['entryHourAssumedUTC']),'session':lambda x:x['sessionAssumedUTC'],'weekday':lambda x:datetime.fromtimestamp(x['entryBarTime'],timezone.utc).strftime('%A'),'body':lambda x:'STRONG' if x['signalBodyATR']>=.45 else 'WEAK','trend':lambda x:'TREND' if x['trendStrength']>=.35 else 'RANGE_OR_WEAK','spread':lambda x:'LOW' if x['spreadATR']<=.1 else 'HIGH','volatility':lambda x:'ABOVE_TRAIN_MEDIAN' if median is not None and x['signalATR']>=median else 'BELOW_TRAIN_MEDIAN'}
  for field,fun in fields.items():
   labels=sorted(set(fun(x) for x in train+val));rows=[]
   for label in labels:
    tr=[x for x in train if fun(x)==label];va=[x for x in val if fun(x)==label];tm=e.metrics(tr);vm=e.metrics(va);ci=e.bootstrap(va)
    negative=tm['n']>=50 and vm['n']>=50 and (tm['expectancyR'] or 0)<0 and ci['upper95'] is not None and ci['upper95']<0
    rows.append({'label':label,'train':tm,'validation':vm,'validationDayBootstrap':ci,'negativeInBothDevelopmentPartitions':negative,'automaticRuleRemoval':False,'status':'WEAK_DISCOVERY_REQUIRES_NEW_PROSPECTIVE_VALIDATION' if negative else 'INSUFFICIENT_EVIDENCE_FOR_REMOVAL'})
   diagnostics[field]=rows
  results.append({'symbol':c['symbol'],'timeframe':c['timeframe'],'model':c['model'],'trainATRMedian':median,'buckets':diagnostics})
 data={'kind':'DEVELOPMENT_ONLY_ENTRY_TIME_REGIME_DIAGNOSTICS','recordedUTC':e.utc(),'combinedSelectionSHA256':e.digest(st['combinedSelectionPath']),'results':results,'changesApplied':[],'reason':'Bucket discovery after model selection is not independent confirmation; no unsupported hour or entry filter is promoted.','holdoutEvaluated':False}
 p=e.save('entry_time_regime_diagnostics',data);e.finish('diagnostics',p,diagnosticsPath=p)

def tick_summary():
 st=e.read(R/'state.json');sel=e.read(st['combinedSelectionPath']);selection_hash=e.digest(st['combinedSelectionPath']);path=st.get('tickProgressPath')
 if not path:return {'completed':0,'total':140,'status':'PENDING','rows':[]}
 progress=e.read(path)
 if progress['selectionHash']!=selection_hash:return {'completed':0,'total':140,'status':'NEW_SELECTION_PENDING','rows':[],'priorDiagnosticProgressPath':path}
 samples=[]
 for batch in progress['batches']:
  d=e.read(batch)
  if d['selectionHash']!=selection_hash:raise RuntimeError('tick_selection_mismatch')
  samples+=d['samples']
 rows=[]
 for c in sel['choices']:
  own=[x for x in samples if x['symbol']==c['symbol']]
  for latency in [5,20]:
   replay=[r for x in own for r in x['results'] if r['latencySeconds']==latency];closed=[x for x in replay if x['status']=='SIMULATED_EXIT'];n=len(closed);wins=sum(x['netR']>0 for x in closed)
   rows.append({'symbol':c['symbol'],'latencySeconds':latency,'samplesAttempted':len(own),'closedSimulations':n,'wins':wins,'winRatePct':100*wins/n if n else None,'expectancyR':sum(x['netR'] for x in closed)/n if n else None,'statuses':{k:sum(x['status']==k for x in replay) for k in set(x['status'] for x in replay)},'nativeRecordStatuses':{k:sum(x['status']==k for x in own) for k in set(x['status'] for x in own)},'completeCoverage':len(own)==20 and n==20,'tickObservedNotActualOrders':True})
 return {'completed':progress['completed'],'total':progress['total'],'status':'COMPLETE' if progress['completed']==progress['total'] else 'IN_PROGRESS','rows':rows,'selectionSHA256':selection_hash,'progressPath':path}

def final():
 st=e.read(R/'state.json');plan=e.read(R/'plan.json')
 if st.get('holdoutPath'):report();return
 if datetime.now(timezone.utc).timestamp()<e.stamp(plan['holdoutReleaseUTC']):print(json.dumps({'stage':'holdout','status':'SEALED','releaseUTC':plan['holdoutReleaseUTC']}));return
 if not st.get('combinedSelectionPath'):raise RuntimeError('combined_selection_required')
 sel=e.read(st['combinedSelectionPath'])
 for tf,en,s in generations():
  if en.read(s['verificationPath'])['violations']:raise RuntimeError('verification_required_'+tf)
 # An exclusive start record prevents a second unseen-test evaluation on crash.
 started=R/'holdout_started.json'
 with started.open('x',encoding='utf-8') as f:json.dump({'openedUTC':e.utc(),'selectionSHA256':e.digest(st['combinedSelectionPath']),'noRepeat':True},f)
 e.state_update(holdoutOpened=True,holdoutStatus='EVALUATION_STARTED')
 results=[];tradepath=R/('combined_holdout_trades_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.jsonl.gz')
 with gzip.open(tradepath,'xb') as f:
  for choice in sel['choices']:
   en=ENGINES[choice['timeframe']];p=en.read(en.R/'plan.json');d=en.load_data(choice['symbol'],p['bounds']['holdout'][1]);ts,cs,sk=en.replay(d,choice['model'],*p['bounds']['holdout']);m=en.metrics(ts,len(cs));ci=en.bootstrap(ts)
   point_goal=m['winRatePct'] is not None and m['winRatePct']>50
   passing=m['n']>=50 and point_goal and (m['expectancyR'] or 0)>0 and (m['profitFactorR'] or 0)>=1.1 and ci['lower95'] is not None and ci['lower95']>0
   result={'symbol':choice['symbol'],'timeframe':choice['timeframe'],'frozenModel':choice['model'],'metrics':m,'dayBootstrap':ci,'holdoutScreenPassed':passing,'developmentScreenPassed':choice['provisionalGate'],'winRatePointGoalPassed':point_goal,'provenWRAbove50':m['wilson95Pct'][0] is not None and m['wilson95Pct'][0]>50,'selectedBeforeTest':True,'tickExecutionValidationComplete':False,'readyForUnattendedLiveTrading':False,'skips':sk}
   results.append(result)
   e.save('holdout_symbol_result',result)
   for row in ts:f.write((json.dumps({**row,'timeframe':choice['timeframe'],'partition':'sealed_holdout'},separators=(',',':'))+'\n').encode())
   for row in cs:f.write((json.dumps({**row,'timeframe':choice['timeframe'],'partition':'sealed_holdout','excludedFromWR':True},separators=(',',':'))+'\n').encode())
 chosen=next(x for x in results if x['symbol']==sel['bestDevelopmentSymbol']);passing=chosen['holdoutScreenPassed'] and chosen['developmentScreenPassed'];decision='PAPER_RESEARCH_CANDIDATE_ONLY' if passing else 'NO_CONFIRMED_STRATEGY; DO_NOT_PROMOTE'
 p=e.save('cycle10_combined_untouched_holdout',{'openedUTC':e.utc(),'selectionSHA256':e.digest(st['combinedSelectionPath']),'results':results,'primaryPreselectedSymbol':sel['bestDevelopmentSymbol'],'decision':decision,'tradePath':str(tradepath),'tradeSHA256':e.digest(tradepath),'finalReselectionAllowed':False,'brokerOrderMutations':0})
 e.finish('holdout',p,holdoutPath=p,holdoutStatus='COMPLETE',status='COMPLETE',nextStage='complete');report()

def csv_write(path,rows):
 # Analysis CSV: JSON archives remain the immutable source of truth.
 keys=list(dict.fromkeys(k for row in rows for k in row))
 with path.open('x',encoding='utf-8-sig',newline='') as f:
  writer=csv.DictWriter(f,fieldnames=keys);writer.writeheader();writer.writerows([{k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v for k,v in row.items()} for row in rows])

def report():
 st=e.read(R/'state.json');sel,groups=selected_groups();final=e.read(st['holdoutPath']) if st.get('holdoutPath') else None;tick=tick_summary();run=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');folder=R/('report_'+run);folder.mkdir();candidates=[];summary=[];allpaths=[]
 for tf,en,s in generations():
  g=en.read(s['gridPath']);allpaths.append({'timeframe':tf,'tradesPath':g['tradesPath'],'SHA256':g['tradesSHA256'],'censoredPath':g['censoredPath']})
  for x in g['rows']:
   for partition,m in x['partitions'].items():candidates.append({'kind':'SIMULATION','timeframe':tf,'symbol':x['symbol'],'modelId':x['model']['id'],'family':x['model']['family'],'bodyATR':x['model']['bodyATR'],'minStopATR':x['model']['minStopATR'],'session':x['model']['session'],'partition':partition,**m})
 csv_write(folder/'model_comparisons.csv',candidates)
 details=[]
 for c in sel['choices']:
  for partition in ['train','validation']:summary.append({'kind':'SIMULATION','symbol':c['symbol'],'timeframe':c['timeframe'],'modelId':c['model']['id'],'family':c['model']['family'],'partition':partition,**c[partition]})
  details.extend({**x,'timeframe':c['timeframe']} for x in groups[c['symbol']])
 if final:
  with gzip.open(final['tradePath'],'rt',encoding='utf-8') as f:
   for line in f:
    x=json.loads(line)
    if not x.get('excludedFromWR'):details.append(x)
  for c in final['results']:summary.append({'kind':'SIMULATION','symbol':c['symbol'],'timeframe':c['timeframe'],'modelId':c['frozenModel']['id'],'family':c['frozenModel']['family'],'partition':'sealed_holdout',**c['metrics']})
 csv_write(folder/'selected_trade_history.csv',details);csv_write(folder/'symbol_summary.csv',summary)
 diag=e.read(st['diagnosticsPath']) if st.get('diagnosticsPath') else None;buckets=[]
 if diag:
  for c in diag['results']:
   for dimension,rows in c['buckets'].items():
    for row in rows:buckets.append({'symbol':c['symbol'],'timeframe':c['timeframe'],'dimension':dimension,'label':row['label'],'status':row['status'],**row['validation']})
 csv_write(folder/'entry_time_diagnostics.csv',buckets)
 # Chart data are simulation-normalized R, never real demo balance.
 curves=[]
 for c in sel['choices']:
  for part in ['validation','sealed_holdout']:
   rs=sorted([x for x in details if x['symbol']==c['symbol'] and x['partition']==part],key=lambda x:x['exitBarTime']);eq=0;peak=0
   for n,x in enumerate(rs,1):eq+=x['netR'];peak=max(peak,eq);curves.append({'symbol':c['symbol'],'partition':part,'closedSimulationIndex':n,'exitUTCUpperBound':x['exitUTCUpperBound'],'equityR':eq,'drawdownR':peak-eq})
 csv_write(folder/'equity_drawdown_data.csv',curves)
 e.read(R/'request.json')
 robustness=st.get('robustness',{});robust_results=[]
 for path in robustness.get('artifacts',[]):
  for x in e.read(path)['results']:robust_results.append({'symbol':x['symbol'],'timeframe':x['timeframe'],'scenario':x['scenario']['id'],'delaySeconds':x['delaySeconds'],'grossWinRatePct':x['grossWinRatePct'],'grossExpectancyR':x['grossExpectancyR'],**x['net']})
 csv_write(folder/'cost_delay_diagnostics.csv',robust_results)
 inventory=e.read(st['inventoryPath']) if st.get('inventoryPath') else None
 if inventory:csv_write(folder/'actual_trade_inventory.csv',inventory['actualRows'])
 adequacy=e.read(st['adequacyPath']) if st.get('adequacyPath') else None
 if adequacy:
  csv_write(folder/'development_evidence_adequacy.csv',adequacy['rows']);csv_write(folder/'entry_time_evidence_adequacy.csv',adequacy['entryTimeBuckets'])
 manifest={'kind':'SIMULATION_RESEARCH_REPORT','recordedUTC':e.utc(),'sourceSelectionSHA256':e.digest(st['combinedSelectionPath']),'summary':summary,'nativeTicks':tick,'fullTradeArchives':allpaths,'chartDataPath':str(folder/'equity_drawdown_data.csv'),'holdout':final,'robustness':robustness,'actualTradeInventoryPath':st.get('inventoryPath'),'automaticPromotion':False,'actualDemoTotalsChanged':False,'files':{x.name:e.digest(x) for x in folder.iterdir() if x.is_file()}}
 if adequacy:manifest['developmentEvidenceAdequacy']={'path':st['adequacyPath'],'SHA256':e.digest(st['adequacyPath']),'newIndependentValidation':False}
 readiness=e.read(st['readinessPath']) if st.get('readinessPath') else None
 if readiness:manifest['preFinalEvidenceIntegrity']={'path':st['readinessPath'],'SHA256':e.digest(st['readinessPath']),'hashChecksPassed':len(readiness['checks']),'nativeValidationArchivesVerified':readiness['nativeValidationArchivesVerified'],'independentNewBacktest':False}
 with (folder/'report.json').open('x',encoding='utf-8') as f:json.dump(manifest,f,ensure_ascii=False,indent=2)
 lines=['# گزارش بک‌تست شبانه — تفسیر ایجنت','',f'زمان: {e.utc()}','تمام معاملات این گزارش شبیه‌سازی‌اند. تعداد هدف ۷۰۰ معاملهٔ واقعی دمو تغییر نمی‌کند.','', '## وضعیت انتخاب',f"گزینهٔ اول توسعه: **{sel['bestDevelopmentSymbol']}**. هیچ یک از هفت گزینه معیار توسعه را پاس نکرده‌اند." if not any(c['provisionalGate'] for c in sel['choices']) else 'گزینه‌های توسعه نیازمند آزمون نهایی‌اند.', 'آزمون نهایی: '+(final['decision'] if final else 'مهروموم؛ بازگشایی فقط از ۸:۴۵ صبح تهران.'),'','## مقایسهٔ نمادها؛ اعتبارسنجی توسعه','|نماد|تایم‌فریم|مدل|N|WR|Expectancy R|PF|DD R|','|---|---|---|---:|---:|---:|---:|---:|']
 fmt=lambda x:'نامعلوم' if x is None else f'{x:.3f}'
 for c in sel['choices']:
  m=c['validation'];lines.append(f"|{c['symbol']}|{c['timeframe']}|{c['model']['family']}|{m['n']}|{fmt(m['winRatePct'])}%|{fmt(m['expectancyR'])}|{fmt(m['profitFactorR'])}|{fmt(m['maxClosedTradeDrawdownR'])}|")
 lines+=['','## داده و روش','- ۶۶۵٬۰۰۰ کندل واقعی M1 از ترمینال؛ M5 فقط از پنج دقیقهٔ کامل و متوالی ساخته شده است.','- ۲۸۰ مقایسهٔ M1 و ۱۶۸ مقایسهٔ M5؛ نمونه‌های مشترک مستقل نیستند و WR همهٔ مدل‌ها با هم جمع نمی‌شود.','- آموزش M1 از ۹ ژوئیه تا ۱۴ اوت؛ روز اول FX ناقص است. آموزش M5 از ۱۰ ژوئیه شروع می‌شود. اعتبارسنجی مشترک: ۱۴ تا ۲۶ اوت. آزمون نهایی: ۲۶ اوت تا ۸ سپتامبر. داده پس از ۸ سپتامبر به علت استفادهٔ قبلی قرنطینه شده است.','- سیگنال با کندل بسته، ورود در کندل بعد، ATR14 و EMA20/60. SL ساختاری سه کندل اخیر با بافر دو تیک؛ فاصله حداقل max(minStopATR×ATR, چهار spread, stop-level بروکر). TP بر اساس سود دلاری حداقل ۲R و گرد کردن به تیک معتبر.','- spread از بیشینهٔ پنج کندل قبلی×۱٫۲۵؛ نیم تیک لغزش ورود و دو تیک لغزش SL. کارمزد فرضی ۷ دلار/لات رفت‌وبرگشت و swap تنش ۱۰ دلار/لات در شب؛ این‌ها هزینه واقعی تاریخی نیستند.','- برخورد همزمان SL/TP در یک کندل به SL محسوب می‌شود؛ معاملات باز در مرز پارتیشن censored و خارج از WR هستند.','- زمان‌های سشن مشروط به ثبات offset تاریخی ۱۸۰ دقیقه‌اند؛ offset فعلی به تنهایی تاریخچه ساعت بروکر را ثابت نمی‌کند.','- نمودارها fixed1R هستند، نه موجودی واقعی یا پورتفوی قابل اجرا با سرمایه کنونی.','', '## ورودهای منتخب برای پژوهش','|نماد|شرط بدنه/ATR|حداقل SL/ATR|سشن فرضی UTC|TP|','|---|---:|---:|---|---|']
 for c in sel['choices']:p=c['model'];lines.append(f"|{c['symbol']}|{p['bodyATR']}|{p['minStopATR']}|{p['session']}|حداقل ۲R ناخالص|")
 lines+=['','تعاریف: RANGE_REJECTION با فاصله EMAها کمتر از ۰٫۲۵ATR و لمس محدودهٔ ۲۰ کندل قبلی و بازگشت ۰٫۲ATR؛ TREND_PULLBACK با فاصله EMAها بیش از ۰٫۳۵ATR و لمس EMA20 و بسته‌شدن در جهت روند؛ BREAK_RETEST با شکست محدوده۲۰ به اندازه۰٫۰۵ATR و بازآزمایی تا پنج کندل بعد. جزئیات دقیق عددی در engine.py و انتخاب منجمد ذخیره شده‌اند.','', '## ضعف‌ها و اصلاحات','- هزینه نسبت به ریسک توقف کوچک، انتخاب بر نمونه کوتاه و ناپایداری walk-forward ضعف‌های اصلی‌اند. مثبت بودن یک جدول توسعه تأیید استراتژی نیست.','- بزرگ کردن تایم‌فریم برای کاهش نویز به صورت آزمایش محدود M5 اجرا شد؛ سوددهی پایدار تأیید نشد.','- هیچ ساعت یا شرط ورود فقط به علت بدترین ردیف حذف نشده است؛ داده دسته‌بندی‌شده در entry_time_diagnostics.csv برای ارزیابی بعدی ذخیره شده است.','- RR ثابت۲ حفظ شد؛ افزایش مصنوعی وین‌ریت با TP کوتاه‌تر با هدف آزمون شما ناسازگار است.','- گزارش قدیمی ۱۰۰ چرخه تکرار یک نتیجه بود؛ در این پژوهش هر مرحله و هر نتیجه مستقل با فایل شواهد ثبت می‌شود.','- تست prefix علیت برای M1 و M5 پاس شد؛ به معنی اثبات اجرای تیک یا سوددهی نیست.','- foldهای walk-forward روش انتخاب را می‌سنجند، نه پایداری قطعی هر مدل منتخب پس از دیدن validation.','',f"## بازپخش تیک واقعی — شبیه‌سازی\n\n{tick['completed']}/{tick['total']} نمونه بررسی شده. فقدان داده یا عدم خروج در پنجرهٔ تیک، برد یا باخت ساختگی محسوب نشده است.",'','## فایل‌های شواهد',f"- انتخاب منجمد: {st['combinedSelectionPath']}",' - report.json: خلاصه، منشأ و hash','- model_comparisons.csv: تمام تنظیمات و پارتیشن‌ها','- selected_trade_history.csv: ورود/خروج، SL/TP، RR، هزینه و علت خروج نمونه منتخب','- entry_time_diagnostics.csv: ساعت، سشن، روز، قدرت ورود و شرایط بازار','- equity_drawdown_data.csv: دادهٔ نمودار شبیه‌سازی','- تاریخچه کامل تمام مدل‌ها در فایل‌های فشردهٔ JSONL با SHA256 در report.json','', '## محدودیت نتیجه','بهترین نماد یا استراتژی تأییدشده هنوز وجود ندارد؛ رتبه‌بندی توسعه با انتخاب برای اجرای زنده متفاوت است. نتیجه آزمون نهایی گزینهٔ اول از پیش منجمدشده را ارزیابی می‌کند و اجازه انتخاب دوباره بهترین ردیف نهایی را نمی‌دهد.','', '[مرجع رسمی محدودیت و ساعت تاریخچه MT5](https://www.mql5.com/en/docs/python_metatrader5/mt5copyratesrange_py)','[پژوهش اصلی بیش‌برازش بک‌تست](https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf)']
 if final:
  lines+=['','## نتیجهٔ آزمون نهایی','|نماد|N|WR|Wilson95|Expectancy R|PF|وضعیت|','|---|---:|---:|---|---:|---:|---|']
  for c in final['results']:
   m=c['metrics'];lines.append(f"|{c['symbol']}|{m['n']}|{fmt(m['winRatePct'])}%|{m['wilson95Pct']}|{fmt(m['expectancyR'])}|{fmt(m['profitFactorR'])}|{c['holdoutScreenPassed']}|")
 lines+=['','## حساسیت به هزینه و کیفیت نمونه',f"{robustness.get('completed',0)} از {robustness.get('total',12)} سناریوی از قبل ثبت‌شده اجرا شده است.",'|نماد|E بدون کارمزد|E کارمزد۳ دلار/لات|E کارمزد۷ دلار/لات|','|---|---:|---:|---:|']
 lookup={(x['symbol'],x['scenario']):x for x in robust_results}
 for c in sel['choices']:
  zero=lookup.get((c['symbol'],'fee0_spread1'),{}).get('expectancyR');low=lookup.get((c['symbol'],'fee3_spread1'),{}).get('expectancyR');base=c['validation']['expectancyR'];lines.append(f"|{c['symbol']}|{fmt(zero)}|{fmt(low)}|{fmt(base)}|")
 lines+=['','کارمزد صفر صرفاً سناریو است؛ صفر بودن کارمزد نمونهٔ واقعی امروز، سیاست تاریخی بروکر را ثابت نمی‌کند. swap فرضی همچنان لحاظ شده است. تفاوت امید ریاضی با وین‌ریت یکی نیست؛ کاهش هزینه به تنهایی شرط ورود را بهتر نمی‌کند. هیچ انتخاب یا قانون منجمدی به علت این جدول عوض نشده است.','سناریوی fee7_spread1 بازاجرای مرجع ثبت‌شده است؛ تطبیق آن بررسی سازگاری محاسبات است و شاهد اعتبارسنجی مستقل یا چرخه بهینه‌سازی تازه محسوب نمی‌شود.','', '## پوشش تیک و WR بازپخش؛ نمونه کوچک','|نماد|تأخیر ثانیه|بررسی‌شده|خروج مشاهده‌شده در شبیه‌سازی|WR|پوشش کامل۲۰ نمونه|','|---|---:|---:|---:|---:|---|']
 for x in tick['rows']:lines.append(f"|{x['symbol']}|{x['latencySeconds']}|{x['samplesAttempted']}|{x['closedSimulations']}|{fmt(x['winRatePct'])}%|{x['completeCoverage']}|")
 lines+=['','WR تیک مشروط به خروج قابل مشاهده در آرشیو است. نمونه‌های طولانی، gap و censored جدا نگه داشته می‌شوند؛ این نرخ جانشین وین‌ریت کل مدل یا شاهد WR بالای۵۰ نیست.']
 if inventory:
  lines+=['','## تاریخچهٔ واقعی؛ جدا از بک‌تست',f"{inventory['currentClosed']} خروج واقعی در دور فعلی و {inventory['priorClosed']} در دور قبلی مستقل بررسی شد. {len(inventory['missingOrUnknownProtection'])} رکورد با SL/TP اولیه صفر یا نامعلوم شناسایی شد.",'SL و TP اولیه از شواهد تطبیق بروکر خوانده شده‌اند؛ پیشنهاد پیش از سفارش به تنهایی شاهد حفاظت واقعی نیست. معاملهٔ دستی قدیمی و نتیجهٔ آن خارج از عملکرد استراتژی است. جزئیات در actual_trade_inventory.csv ذخیره شده است.']
 if adequacy:
  manifest_note='این تحلیل توصیفی پس از انتخاب است؛ اعتبارسنجی مستقل تازه یا تغییر قانون نیست.'
  lines+=['','## کفایت شواهد و ضعف ورود',manifest_note,f"{adequacy['uniqueValidationTradesAudited']} معاملهٔ اعتبارسنجی از نظر زمان علی، SL/TP، RR و جمع نتایج تطبیق شد؛ تخلف ثبت‌شده صفر است.",'|نماد|E آموزش|E اعتبارسنجی|روز اعتبارسنجی|هزینهٔ کارمزد و swap میانه/R|ساعت با حداقل۵۰ معامله در هر دو بخش|','|---|---:|---:|---:|---:|---:|']
  for x in adequacy['rows']:lines.append(f"|{x['symbol']}|{fmt(x['trainingExpectancyR'])}|{fmt(x['validationExpectancyR'])}|{x['validationDays']}|{fmt(x['commissionAndSwapCostRMedian'])}|{x['entryAndTimeGroupAdequacy']['hour']['bucketsWith50TrainAnd50Validation']}|")
  lines+=['','مثبت شدن عملکرد طلا در اعتبارسنجی پس از آموزش زیان‌ده به تنهایی پایداری را ثابت نمی‌کند. گروه‌های ساعت با نمونهٔ کافی مشخص شده‌اند؛ کمبود نمونه مجوز حذف یا انتخاب بهترین ساعت نیست. اثر کارمزد از اثر کیفیت ورود جداست. سقف فرضی کارمزد برای صفر شدن E و جزئیات پوشش تیک در development_evidence_adequacy.csv است؛ این سقف سیاست واقعی بروکر یا پیش‌بینی سود نیست.',f"منشأ تحلیل تکمیلی: {st['adequacyPath']}"]
 if readiness:lines+=['','## یکپارچگی شواهد پیش از آزمون نهایی',f"{len(readiness['checks'])} تطبیق SHA256 شامل {readiness['nativeValidationArchivesVerified']} آرشیو تیک موجود انجام شد. دادهٔ قیمت آزمون نهایی برای این کنترل decode نشده است. کنترل یکپارچگی، نقص پوشش تیک یا کمبود شواهد سوددهی را رفع نمی‌کند.",f"شاهد ثبت‌شده پیش از بازگشایی: {st['readinessPath']}"]
 with (folder/'REPORT.md').open('x',encoding='utf-8') as f:f.write('\n'.join(lines)+'\n')
 e.state_update(latestReport=str(folder/'REPORT.md'),latestReportJSON=str(folder/'report.json'),latestReportFolder=str(folder))
 print(json.dumps({'stage':'combined_report','reportPath':str(folder/'REPORT.md'),'folder':str(folder),'final':bool(final),'nativeSamplesCompleted':tick['completed']}))

if __name__=='__main__':
 {'select':select,'diagnostics':diagnostics,'report':report,'final':final,'ticks-summary':lambda:print(json.dumps(tick_summary()))}[sys.argv[1]]()

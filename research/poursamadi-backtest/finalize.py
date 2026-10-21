"""Persist backtest outcome/report; does not access or mutate MT5."""
import json,hashlib
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path('E:/GPT/Inves/research/poursamadi-backtest')
W=Path('E:/GPT/Inves')
now=datetime.now(timezone.utc).isoformat()
result_path=ROOT/'backtest_result_20261008T153525891254Z.json'
screen_path=ROOT/'current_screen_20261008T153553201966Z.json'
result=json.loads(result_path.read_text(encoding='utf-8'))
screen=json.loads(screen_path.read_text(encoding='utf-8'))
model=json.loads((ROOT/'model-v1.json').read_text(encoding='utf-8'))
decision={
 'mode':'backtest','symbol':'XAUUSD','timeframe':'M1',
 'candle_time_utc':'2026-10-07T23:59:00Z',
 'module_results':[
  {'strategy':'SP2L','status':'INDETERMINATE','source_ids':['V5'],'reason':'Exact P-Gap and spike/correction boundaries are unresolved; not tested as teacher replication.'},
  {'strategy':'PRO_BTB','status':'INDETERMINATE','source_ids':['V6'],'reason':'Exact key-level/breakout quality and six entry modes unresolved; not tested as teacher replication.'},
  {'strategy':'MICROMAP','status':'INDETERMINATE','source_ids':['V4'],'reason':'Teacher exact quantitative definitions unresolved. A separately user-approved agent interpretation was frozen and backtested; six historical setups, zero risk-eligible trades.'},
  {'strategy':'TIME','status':'INDETERMINATE','source_ids':['V2'],'reason':'Official partial priority windows tagged separately in fixed UTC+3. No hard signal or full eleven-window replication.'}
 ],'direction':'NONE','entry':None,'stop_loss':None,'take_profit':None,
 'time_reference':'UTC timestamps; measured broker/reference UTC+3 separately recorded',
 'risk_pct':1,'decision':'NO_TRADE',
 'unresolved':['Full seven videos not watched/transcribed.','Numerical source-method definitions unresolved.','No risk-eligible OOS trades or prospective fills.'],
 'notes':'Approved experiment is explicitly labeled تفسیر ایجنت. Its historical holdout failed the registered acceptance gate. No orders were sent.'
}
decision_path=ROOT/'source-method-decision-v1.json'
with decision_path.open('x',encoding='utf-8') as f:json.dump(decision,f,ensure_ascii=False,indent=2)
rows='\n'.join(f"| {x['entryUTC']} | {x['entry']:.2f} | {x['SL']:.2f} | {x['TP']:.2f} | {x['totalRiskUSDMin']:.2f} | {x['netUSDMin']:.2f} | {x['netR']:.3f} |" for x in result['rows'])
report=f'''# گزارش بک‌تست — تفسیر ایجنت

تاریخ ثبت: {now}

## نتیجه و مرحلهٔ ترید

مدل `{model['version']}` روی طلا و M1 اجرا شد. این مدل برداشت عددی تأییدشده توسط کاربر است؛ بازتولید دقیق روش مدرس یا نتیجهٔ تماشای هفت ویدیو نیست.

- ۲۹٬۰۳۶ کندل از ۸ سپتامبر تا پایان ۷ اکتبر ۲۰۲۶؛ ۶ ستاپ.
- ۲ ستاپ با تأخیر ۲۰ ثانیه، خبر و تیک واقعی قابل بازپخش بودند؛ هر دو به علت حداقل حجم نسبت به بودجهٔ ریسک رد شدند.
- تعداد معاملات قابل اجرای پرتفوی: **صفر** در آموزش، اعتبارسنجی و خارج‌نمونه. PF، نرخ برد و امید ریاضی قابل برآورد نیستند. PnL و افت عددی صفر در این پرتفوی‌ها ناشی از معامله نکردن‌اند و شاهد عملکرد مطلوب نیستند.
- مجموع تشخیصی دو معاملهٔ حداقل حجم: **۲٫۳۶ دلار زیان خالص**؛ سود/زیان قبل از کارمزد −۲٫۲۲ و کارمزد فرضی ۰٫۱۴ دلار. این معاملات خارج از بودجهٔ حساب‌اند و بازده قابل اجرای پرتفوی نیستند.
- `researchGatePassed=false`: حداقل ۳۰ معاملهٔ خارج‌نمونه، سود خالص مثبت و PF حداقل ۱٫۱ احراز نشدند. دو معامله برای حکم دربارهٔ سوددهی کافی نیستند.
- بررسی دمو در {screen['recordedUTC']}: حساب متصل و مجاز، equity=100.55 USD، صفر پوزیشن و سفارش، سن quote={screen['quoteAgeSeconds']:.3f} ثانیه؛ از زمان ثبت مدل هیچ ستاپ تازهٔ این نسخه تشکیل نشده بود. **سفارش ارسال‌شده: صفر**.
- مرحلهٔ ورود: `BLOCKED_ENTRY` با علت‌های `research_gate_failed` و `no_fresh_active_setup`. اجرای قدیمی و اتوماسیون متوقف‌شده از سر گرفته نشدند.

## مدل ثبت‌شده پیش از مشاهدهٔ نتایج

فقط خرید و اولین ورود MicroMAP: دو کندل صعودی متوالی، سهم بدنه حداقل ۰٫۶۵، محل بسته شدن حداقل ۰٫۷۵ و حرکت خالص حداقل دو ATR14 قبل از اسپایک. سپس ۲ تا ۵ کندل با سقف‌های پی‌درپی پایین‌تر، دامنه حداکثر ۰٫۷ دامنهٔ متوسط اسپایک و اصلاح حداکثر ۵۰٪ حرکت خالص.

اولین bid که سقف آخرین کندل بستهٔ میکروکانال +۰٫۰۲ را رد کند، ستاپ را مصرف می‌کند. تأخیر ۲۰ ثانیه و برقرار ماندن شکست در ورود اعمال شد؛ تلاش مجدد وجود ندارد. SL پشت کف همان کندل −۰٫۰۲؛ TP=2R و خروج حداکثر ۶۰ ثانیه. TP و تمام آستانه‌های عددی **فرض ایجنت** هستند. نام H1 در شناسه یعنی اولین ورود این آزمایش؛ تایم‌فریم آن **M1** است.

منبع ساختار کلی: [صفحهٔ رسمی MicroMAP](https://poursamadi.com/micromap/). ساعت‌های اولویت فقط برچسب با مرجع UTC+3 هستند: [صفحهٔ رسمی استراتژی زمانی](https://poursamadi.com/time-analysis-strategy/). ساعت مناسب به‌تنهایی ورود ایجاد نمی‌کند. SP2L و Pro BTB به علت ابهام تعریف عددی وارد این بک‌تست نشدند.

## داده، اجرا و کنترل خطر

OHLC بومی MT5 برای غربال و تیک تاریخی واقعی bid/ask برای ورود و خروج؛ کندل باز به‌عنوان بسته مصرف نشده است. شکاف تیک بیش از ۱۰ ثانیه یا پوشش نامعتبر موجب رد می‌شود. ۲۳ فاصلهٔ غیر یک‌دقیقه‌ای بین کندل‌ها ثبت شد؛ بخش‌های مجاور ناپیوستگی برای محاسبهٔ ساختار استفاده نشدند. تقویم تاریخی ۱٬۱۸۰ رکورد داشت؛ ۴۳ پنجرهٔ مسدود خبر High USD با ±۱۵ دقیقه اعمال شد.

تقسیم زمانیِ از پیش ثبت‌شده:

| بخش | شروع UTC | پایان انحصاری UTC | معاملات مجاز |
|---|---|---|---:|
| آموزش | 2026-09-08 | 2026-09-22 | 0 |
| اعتبارسنجی | 2026-09-22 | 2026-10-01 | 0 |
| خارج‌نمونه | 2026-10-01 | 2026-10-08 | 0 |

این بخش‌ها پرتفوی‌های فرضی مستقل با موجودی اولیهٔ ۱۰۰٫۵۵ دلار دارند؛ هیچ قله یا شمارنده‌ای در حساب واقعی بازنشانی نشده است. بخش خارج‌نمونه تاریخی پیش از نتیجه کنار گذاشته شد؛ فورواردتست یا fill واقعی نیست. پس از این مشاهده، همین بخش برای نسخهٔ بعد دیگر خارج‌نمونهٔ دست‌نخورده نیست.

حجم رو به پایین، یک پوزیشن، ۱۲ fill و دو زیان در هر تاریخ UTC، توقف ۲٪ از قلهٔ حفظ‌شده. بودجهٔ اولیه:

`min(100.55×1%, 100.55−100.55×98%, 100.55×10%) = 1.0055 USD`

حداقل حجم ۰٫۰۱ و قرارداد ۱۰۰؛ native OrderCalcProfit تأیید کرد یک دلار تغییر قیمت با ۰٫۰۱ لات = یک دلار سود/زیان قیمت. مارجین با OrderCalcMargin بومی محاسبه و به ۵۰٪ free margin محدود شد. ذخیرهٔ هزینه در حداقل حجم ۰٫۲۷ دلار است: ۰٫۱۰ لغزش +۰٫۱۰ افزایش spread +۷ دلار کارمزد رفت‌وبرگشت به ازای لات. ask برای ورود و bid برای خروج، لغزش نامساعد ۰٫۰۵ در هر سمت و سقف spread=۰٫۵ اعمال شد.

## دو شبیه‌سازی تشخیصی ردشده

حجم هر ردیف ۰٫۰۱؛ ریسک شامل ذخیرهٔ هزینه است. نگهداری هر دو با خروج زمانی حدود ۶۰ ثانیه پایان یافت.

| ورود UTC | ورود | SL | TP | ریسک USD | خالص USD | خالص R |
|---|---:|---:|---:|---:|---:|---:|
{rows}

ریسک ۳٫۶۷ و ۴٫۰۹ دلار هم از بودجهٔ فعال ۱٫۰۰۵۵ و هم از headroom افت ۲٫۰۱۱ دلار بیشتر است؛ سقف مجاز ۱۰٪ این دو محدودیت را حذف نمی‌کند. SL برای جا دادن حجم تنگ نشده است.

چهار ستاپ دیگر: یک شکست ایجاد نشد؛ دو شکست طی تأخیر اجرا از دست رفتند؛ یک مورد در پنجرهٔ خبر USD بود. اجرای بدون تأخیر فقط تشخیص حساسیت بود و به‌عنوان نتیجهٔ قابل اجرا انتخاب نشد.

## محدودیت‌ها و تصمیم پژوهشی

نمونهٔ شش ستاپ بسیار کوچک است. سخت‌گیری عددی این تفسیر ممکن است فرصت‌ها را کم کرده باشد؛ این نتیجه دربارهٔ تمام روش‌های مدرس نیست. مشخصات قرارداد، اهرم و طبقه‌بندی اخبار فعلی برای گذشته فرض شده‌اند؛ هزینه و تأخیر واقعی تاریخی در دسترس نیستند. offset اندازه‌گیری‌شدهٔ فعلی +۱۸۰ دقیقه برای تاریخچه استفاده شد و رژیم تاریخی DST مستقلاً بازسازی نشد. MAE/MFE از تیک مشاهده‌شده‌اند و فاصله‌های فاقد تیک ناشناخته باقی می‌مانند.

نسخهٔ بعد باید با دادهٔ توسعهٔ جداگانه، تعریف دقیق‌تر اسپایک/میکروکانال و امکان‌پذیری هزینه در حداقل حجم ثبت شود؛ سپس روی دادهٔ مستقل یا آینده آزمون شود. تغییر پارامتر برای زیبا شدن نتیجهٔ همین خارج‌نمونه، تأیید مستقل ایجاد نمی‌کند. افزایش ریسک فعال بر اساس این نمونه توجیه ندارد.

## اصلاحات پیاده‌سازی و بازتولید

دو اصلاح ثبت‌شده پارامترهای راهبرد را تغییر ندادند: تکمیل تیک تا پایان تأخیر + نگهداری برای جلوگیری از خروج سانسورشده؛ و ارزیابی دو کندل حداقل میکروکانال در انتهای داده بدون نیاز به کندل‌های آینده تا سقف پنج. نتایج اولیه حفظ و با فایل‌های correction علامت‌گذاری شدند؛ نتیجهٔ معتبر این گزارش فایل زیر است.

- [مدل ثبت‌شده](/E:/GPT/Inves/research/poursamadi-backtest/model-v1.json)
- [پروتکل و هش تاریخچه](/E:/GPT/Inves/research/poursamadi-backtest/protocol-v1.json)
- [فرض‌های تأخیر](/E:/GPT/Inves/research/poursamadi-backtest/execution-assumptions-v1.json)
- [نتیجهٔ کامل](/E:/GPT/Inves/research/poursamadi-backtest/{result_path.name})
- [بررسی تازهٔ دمو](/E:/GPT/Inves/research/poursamadi-backtest/{screen_path.name})
- [تصمیم روش منبع](/E:/GPT/Inves/research/poursamadi-backtest/source-method-decision-v1.json)
- [کد بک‌تست](/E:/GPT/Inves/research/poursamadi-backtest/backtest.py)

بازپخش فقط تاریخچه و محاسبات را می‌خواند؛ سفارش‌گذاری ندارد. snapshotهای تیک و خروجی‌ها با ایجاد انحصاری حفظ شده‌اند.
'''
# Windows absolute links have a drive prefix; do not prefix an extra slash.
report=report.replace('](/E:/','](E:/')
report_path=ROOT/'Report_FA.md'
with report_path.open('x',encoding='utf-8') as f:f.write(report)
manifest={'recordedUTC':now,'type':'BACKTEST_COMPLETE_DEMO_ENTRY_BLOCKED','modelVersion':model['version'],'label':'تفسیر ایجنت','teacherExactRules':False,'researchGatePassed':False,'backtestResult':str(result_path),'currentScreen':str(screen_path),'report':str(report_path),'ordersSubmitted':0,'realAccountEquityUSD':screen['account']['equity'],'positions':len(screen['positions']),'orders':len(screen['orders']),'entryBlockers':screen['reasons'],'sourceSHA256':hashlib.sha256((ROOT/'backtest.py').read_bytes()).hexdigest(),'supersededResults':['backtest_result_20261008T153203165392Z.json','backtest_result_20261008T153310722513Z.json'],'automationResumed':False}
manifest_path=ROOT/'task-outcome-v1.json'
with manifest_path.open('x',encoding='utf-8') as f:json.dump(manifest,f,ensure_ascii=False,indent=2)
state_path=W/'Trading_Manager_State.json'
state=json.loads(state_path.read_text(encoding='utf-8'))
checkpoint={'recordedUTC':now,'reason':'Record the user-approved new backtest task and failed demo-entry gate; preserve stopped execution, peak/counters, previous configuration and all journal history.','stateBefore':state,'manifest':manifest}
checkpoint_path=W/'trading-journal'/('poursamadi_backtest_review_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.json')
with checkpoint_path.open('x',encoding='utf-8') as f:json.dump(checkpoint,f,ensure_ascii=False)
state['stage']='BACKTEST_COMPLETE_ENTRY_BLOCKED'
state['last_exposure_check_utc']=screen['recordedUTC']
state['last_research_decision_path']=str(manifest_path)
state['last_backtest_path']=str(result_path)
state['last_backtest_report_path']=str(report_path)
state['pending_strategy_version']=model['version']
state['latest_task_authorization']='User requested backtest then demo trade, and explicitly approved a labeled agent interpretation. Exact teacher replication is not authorized to be invented.'
state['next_action']='Entry blocked by failed registered research gate and no fresh setup. Preserve current risk/peak. Develop any revised experiment on development data; use new independent holdout or prospective paper data. Do not reuse reviewed October 1–7 as untouched validation.'
state['research_queue'].append({'proposal_version':model['version'],'proposal_path':str(ROOT/'model-v1.json'),'result_path':str(result_path),'status':'backtested_no_risk_eligible_trades_not_promoted','research_gate_passed':False,'next_action':state['next_action']})
state_path.write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'report':str(report_path),'manifest':str(manifest_path),'checkpoint':str(checkpoint_path),'executionEnabled':False,'runStatus':state['run_status'],'stage':state['stage']}))

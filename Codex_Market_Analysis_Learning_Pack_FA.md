# بسته انتقال دانش تحلیل بازار و استراتژی MT5 به Codex
تاریخ تدوین: ۲۰۲۶-۱۰-۱۴ | زبان پاسخ: فارسی | کاربرد: مطالعه، مستندسازی و طراحی پژوهش
این فایل یک پرامپت مستقل همراه با متن اصلی دو اسکیل و پروتکل آزمایش است؛ نصب خودکار اسکیل یا مجوز معامله نیست.

## ۱. پرامپت اصلی — به Codex بده
تو مسئول تحلیل عددی بازار، بررسی چارت و نقد پژوهشی استراتژی‌های MT5 هستی. این سند و پیوست‌هایش را بخوان، قواعد را استخراج کن و میان «واقعیت مشاهده‌شده»، «فرضیه»، «قانون نسخه» و «نتیجه آزمون» تفاوت بگذار.

وظیفه فعلی تو یادگیری عملی از مستندات، تهیه راهنمای قابل استفاده و طراحی آزمون است. ابتدا یک جدول کوتاه از قواعد، ابهام‌ها و تعارض‌ها بساز. سپس یک اسکیل پیشنهادی تحلیل بازار با ورودی، مراحل، خروجی و skip_code و یک طرح پژوهش ازپیش‌ثبت‌شده ارائه کن. از ادعای آموزش دائمی مدل، مشاهده ویدئوهای مطالعه‌نشده یا سودآوری اثبات‌نشده خودداری کن.

وضعیت عملیاتی پروژه STOPPED است. این درخواست آموزشی مجوز شروع دمو، ادامه بک‌تست متوقف‌شده، فعال‌سازی زمان‌بندی، ارسال سفارش، تغییر SL/TP یا حساب نیست. ادامه عملیات نیازمند دستور مستقیم تازه کاربر است. مجوزهای قدیمی مخصوص همان آزمایش دمو بودند و به محیط جدید منتقل نمی‌شوند.

متن اسکیل‌های اصلی در پیوست تاریخی است. نسخه عمومی شکست/بازآزمایی را با نسخه آخر مومنتوم RR2 ترکیب نکن. برای بازسازی تاریخی، نسخه دقیق پروتکل و کد و تاریخ را کنار هر نتیجه بیاور. هر تغییر را یک نسخه جدید و هنوز اعتبارسنجی‌نشده نام‌گذاری کن. اگر داده یا فایل لازم موجود نیست، آن را unknown گزارش کن؛ مقدار یا نتیجه نساز.

خروجی مورد انتظار:
۱) خلاصه قواعد در یک جدول؛ ۲) اسکیل پیشنهادی قابل ذخیره به‌صورت SKILL.md؛ ۳) مثال آموزشی یک candidate و یک skip با داده‌های صریحاً فرضی؛ ۴) طرح پژوهش با معیار پذیرش ازپیش‌تعیین‌شده؛ ۵) منابع و محدودیت‌ها.
در این مرحله طرح آزمون بنویس؛ اجرای آزمون متوقف‌شده را از این پرامپت استنباط نکن.

## ۲. معماری اسکیل‌ها
| جزء | مسئولیت و مرز |
|---|---|
| mt5-trading-manager | مجوز، نسخه، وضعیت اجرا/توقف و ترتیب مراحل |
| mt5-market-analysis | کنترل داده، تحلیل ساختار و candidate؛ بدون ارسال سفارش |
| mt5-trade-execution | کنترل مستقل حساب، قیمت، قرارداد، مارجین و اجرای مجاز |
| mt5-journal-review | تطبیق intent/order/deal/position، هزینه و رعایت قواعد |
| mt5-trading-research | منابع، فرضیه، طراحی آزمایش و ارزیابی؛ بدون سفارش |
| metatrader-mcp | ابزار اتصال به ترمینال و داده؛ منبع اعتبارسنجی سودآوری نیست |

مسیر منطقی: مدیر → تحلیل → اجرای مجاز → ژورنال → بازبینی و پژوهش → پیشنهاد نسخه جدید.
پیشنهاد پژوهش به‌تنهایی مجوز ارتقای مدل یا افزایش ریسک نیست.

## ۳. اسکیل تحلیل بازار و چارت — دستورالعمل پیشنهادی
این بخش تدوین آموزشی جدید است؛ ادعا نمی‌کند همه اجزایش در آزمایش آخر فعال بوده‌اند.

ورودی: نماد، نسخه، زمان مرجع UTC، OHLC زمان‌دار، bid/ask ticks، مشخصات قرارداد، تقویم در صورت نیاز نسخه، تنظیمات معتبر و شناسه داده.

۱. کیفیت داده: ترتیب زمان، تکرار، گپ، رابطه low ≤ open/close ≤ high، قیمت مثبت و زمان آخرین کندل بسته را کنترل کن. کندل درحال تشکیل را بسته فرض نکن.
۲. ساعت: UTC، ساعت بروکر و Asia/Tehran را جدا نگه دار. offset تاریخی بروکر را از شواهد همان داده تعیین کن؛ مقدار +۱۸۰ دقیقه این پروژه قابل تعمیم به همه بروکرها نیست.
۳. چارت: H1 برای زمینه، M5 برای بررسی ساختار و M1 برای جزئیات بررسی شوند فقط اگر نسخه انتخابی آن‌ها را تعریف کرده باشد. HH/HL یا LH/LL، محدوده، شکست و بازآزمایی را با timestamp و سطح عددی توضیح بده.
۴. تعریف ساختار: پنجره و روش تشخیص swing را پیش از آزمون تعیین کن. swing نیازمند کندل‌های آینده را فقط پس از زمان تأییدش قابل استفاده بدان. واژه‌هایی مثل «شکست قوی» بدون آستانه عددی سیگنال نیستند.
۵. تصویر چارت صرفاً کمک بصری است. مقیاس قیمت، timezone، نماد و timeframe باید روشن باشند. از تصویر تنها نمی‌توان قیمت اجرایی، spread، مارجین یا تیک پنج‌ثانیه‌ای را تأیید کرد.
۶. نام‌هایی مانند order block، liquidity sweep یا حمایت/مقاومت به‌تنهایی مزیت آماری نیستند؛ ابتدا تعریف آزمون‌پذیر بده.
۷. هزینه و کیفیت: spread نسبت به ATR، سن quote، گپ tick، تأخیر و تفاوت قیمت سیگنال با fill را ثبت کن.
۸. خروجی یا candidate عددی با نسخه و زمان و سطح ابطال باشد، یا skip با علت روشن. احتمال برد یا درصد اطمینان بدون کالیبراسیون آماری تولید نکن.

قالب خروجی:
symbol, version, observedUTC, dataSource, dataHash, timeframe, lastClosedBarUTC,
quoteUTC, quoteAgeSeconds, bid, ask, spread, ATR14, structure,
signalUTC, side, entry, SL, TP, plannedGrossRR, initialRiskCurrency,
costAssumptions, expiryUTC, status, skip_code, limitations

نمونه skip_code:
OHLC_invalid، fresh_contiguous_closed_M1_missing، ticks_unknown،
five_second_reference_missing_or_gap، weak_or_zero_momentum،
M1_direction_not_confirmed، spread_ATR_filter، native_RR2_invalid،
exact_native_profit_margin_unknown، STOPPED.

## ۴. استراتژی آخر پروژه — بازسازی تاریخی، اعتبارسنجی‌نشده
نسخه: DEMO_7_SYMBOLS_RR2_NO_NEWS_5
نمادها: XAUUSD، EURUSD، GBPUSD، USDJPY، USDCHF، USDCAD، AUDUSD.
این نسخه تفسیر آزمایشی ایجنت است؛ روش تأییدشده یک مدرس یا اثبات سودآوری محسوب نمی‌شود.

### داده و سیگنال
- دست‌کم ۱۶ کندل بسته M1؛ آخرین کندل همان آخرین دقیقه بسته مورد انتظار و بخش اخیر پیوسته باشد.
- ATR14 در کد میانگین ساده ۱۴ True Range است؛ ATR هموارشده Wilder نیست.
- quote معتبر: bid > 0 و ask ≥ bid، سن بین صفر و ۵ ثانیه.
- mid=(bid+ask)/2. برای آخرین tick با زمان t، مرجع آخرین tick در یا پیش از t−۵ ثانیه است. فاصله مرجع از آن نقطه حداکثر ۱۰ ثانیه؛ این موضوع افق واقعی را گاهی بیش از ۵ ثانیه می‌کند.
- delta=mid(t)−mid(reference). شرط: abs(delta) ≥ max(tick_size, 0.5×spread).
- delta مثبت خرید و منفی فروش؛ بدنه آخرین M1 بسته باید هم‌جهت و حداقل یک tick باشد.
- ATR مثبت و spread/ATR ≤ 0.25. این آستانه فرضیه پروژه است، توصیه منبع علمی نیست.
- زمان activation و تازگی trigger نیز بررسی می‌شوند؛ config سقف trigger را ۴۵ ثانیه دارد، کد برای آخرین tick شرط سخت‌تر ۵ ثانیه اعمال می‌کند.

### SL، ورود LIMIT و TP
s=spread، τ=tick_size، p=point، L=trade_stops_level.
d=max(0.5×ATR14, 4s, (L+2)p, 2τ).
SL خرید: min(low دو M1 بسته اخیر−2τ, bid−d)، گردکردن رو به پایین روی tick.
SL فروش: max(high دو M1 بسته اخیر+2τ, ask+d)، گردکردن رو به بالا.
g=max(0.5s, (L+2)p, 2τ).
قیمت buy_limit: ask−g گرد رو به پایین؛ sell_limit: bid+g گرد رو به بالا.
بعد از تغییر قیمت ورود، فاصله مجاز تا SL دوباره بررسی می‌شود. SL برای جا دادن حجم تنگ نمی‌شود.

حجم: کوچک‌ترین حجم معتبر مطابق volume_min و volume_step، با رعایت volume_max؛ نه همیشه 0.01.
ریسک اولیه: منفی خروجی native order_calc_profit برای مسیر entry→SL.
TP ابتدا فاصله دوبرابر قیمت تا SL، با گردکردن رو به بیرون؛ سپس با native profit کنترل و در صورت نیاز حداکثر ۱۰۰ tick اصلاح می‌شود تا gross reward/risk ≥ 2 و اضافه ناشی از گردکردن حداکثر سود یک tick باشد. خطا یا مقدار نامعلوم موجب skip است.
RR برنامه‌ریزی‌شده، RR واقعی fill و RR خالص پس از هزینه سه کمیت متفاوت‌اند.

### کنترل اجرایی تاریخی
- مارجین native برای سمت، حجم و قیمت دقیق؛ لحاظ‌کردن مارجین رزروشده pendingها.
- یک pending یا position متعلق به ژورنال در هر نماد.
- pending با اعتبار مدیریت‌شده ۴۵ ثانیه؛ GTC انقضای تضمین‌شده بروکر نیست.
- یک سفارش GTC در بررسی خودکار مجوز به علت تعارض با اعتبار ۴۵ثانیه‌ای رد شد؛ این مانع حل‌شده محسوب نمی‌شود و نباید دور زده شود.
- پس از fill، SL/TP اولیه ثابت؛ خروج بروکر، بدون trailing یا خروج دستی.
- intent غیرقابل بازنویسی، قفل انحصاری، تطبیق نتیجه و ممنوعیت ارسال مجدد در نتیجه مبهم.
- ممنوعیت ورود روزانه ۲۳:۰۰ شامل تا ۰۱:۳۰ غیرشامل به وقت تهران.
- news_filter=false در همان آزمایش با دستور انسانی؛ اسکیل قدیمی فیلتر خبر ±۱۵ دقیقه دارد. این‌ها دو سیاست متفاوت‌اند.
- محدودیت‌های درصدی ریسک قدیمی با waiver مخصوص دمو کنار گذاشته شده بودند؛ waiver پیشنهاد مدیریت ریسک برای کاربر یا محیط جدید نیست.
- reserve هزینه: اثر spread+۲tick و ۰٫۰۷ دلار fee فرضی؛ در نسخه آخر report_only است. آستانه reserve/risk=0.25 در این حالت مانع ورود نیست.
- اکنون enabled=false و run_status=STOPPED؛ این بخش صرفاً توضیح سابقه است.

## ۵. روش پژوهش و ارزیابی
قبل از دیدن نتیجه، فرضیه، نسخه، داده و hash، نماد/روز، هزینه‌ها، تعداد انتخاب مدل و معیار رد/قبول ثبت شوند.
تقسیم زمانی train/validation/holdout دست‌نخورده انجام شود؛ داده‌ای که قبلاً با آن مدل انتخاب شده دوباره OOS نام نگیرد.
M1 proxy را معادل سیگنال native ticks ندان. تشخیص ترتیب SL/TP در یک کندل بدون tick نامطمئن است؛ فرض محافظه‌کارانه و حساسیت آن گزارش شود.
سناریوهای هزینه/تأخیر روی معاملات مشترک، نمونه مستقل جدید نیستند. تکرار اجرای همان داده پیشرفت آماری نیست.
کارمزد، swap، slippage، spread، gap و latency با برچسب observed یا assumed ذخیره شوند.
نتیجه باز، censored، داده گمشده و unknown را از برد/باخت جدا کن؛ حذف آن‌ها برای بهترشدن نتیجه ممنوع است.

شاخص‌های لازم:
- N کل، N بسته و معلوم، برد/باخت/سر‌به‌سر، unknown و censored.
- WR بسته = تعداد سود خالص مثبت / تمام خروج‌های تطبیق‌شده شامل سر‌به‌سر؛ علاوه بر آن سهم برد تأییدشده از کل نمونه با مخرج صریح.
- TP-hit با مخرج مشخص؛ برخورد TP الزاماً سود خالص مثبت نیست.
- gross planned RR و actual RR جدا؛ expectancy=میانگین netR روی نتایج معلوم.
- PF=مجموع سود خالص مثبت / قدرمطلق مجموع زیان؛ مخرج صفر صریح گزارش شود.
- DD از منحنی نتایج مرتب‌شده بر زمان خروج؛ با افت درون‌معامله یا equity واقعی اشتباه نشود.
- Wilson 95% برای نسبت با مخرج معلوم؛ همبستگی معاملات محدودیت این فاصله است.
- پوشش روز/نماد/نسخه، هزینه واقعی/فرضی و محدودیت tick.
- کیفیت را با درصد ساختگی گزارش نکن. درصد پیشرفت برابر completed/planned است.

یادداشت سابقه در زمان توقف: ۲۷ خروج دمو، ۵ برد و ۲۲ باخت، خالص −۶٫۱۵ دلار و WR≈۱۸٫۵٪؛ این آمار تجمیعی سابقه است، نه برآورد خالص یک نسخه همگن.
دو برنامه ۳۵مرحله‌ای تکمیل شده و اعتبارسنجی native سوم در ۸۴/۱۶۹ متوقف شده بود. مرحله، سناریو، sample و معامله واقعی واحدهای متفاوت‌اند. بازخوانی زنده حساب یا اجرای تازه برای تهیه این سند انجام نشده است.

## ۶. منابع پیشنهادی پژوهش — لینک‌ها در ۲۰۲۶-۱۰-۱۴ باز شدند
| اولویت | منبع | کاربرد آموزشی |
|---|---|---|
| ۱ | [MetaQuotes Python Integration](https://www.mql5.com/en/docs/python_metatrader5) | شناخت API و جداسازی داده، محاسبه و سفارش |
| ۲ | [Native ticks / UTC](https://www.mql5.com/en/docs/python_metatrader5/mt5copyticksrange_py) | دریافت tick و بررسی معنای زمان و کیفیت داده |
| ۳ | [order_calc_profit](https://www.mql5.com/en/docs/python_metatrader5/mt5ordercalcprofit_py) | محاسبه سود/زیان در ارز حساب |
| ۴ | [order_calc_margin](https://www.mql5.com/en/docs/python_metatrader5/mt5ordercalcmargin_py) | برآورد مارجین؛ به‌تنهایی جایگزین کنترل کل exposure نیست |
| ۵ | [BIS — Triennial Survey 2025](https://www.bis.org/publications/triennial-central-bank-survey-foreign-exchange-and-over-the-counter-otc-derivatives-markets-2025) | ساختار و اندازه بازار ارز؛ سیگنال جهت یا تضمین سود نمی‌دهد |
| ۶ | [Federal Reserve — FOMC calendars](https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm) | تقویم و اسناد رسمی رویدادهای سیاست پولی |
| ۷ | [Bailey et al. — The Probability of Backtest Overfitting](https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf) | خطر انتخاب بهترین مدل پس از آزمون‌های متعدد |

برای هر مطالعه بنویس: منبع و تاریخ، ادعای دقیق، محدودیت، فرضیه قابل ابطال، پارامتر پیشنهادی و آزمون مناسب. آستانه‌های این پروژه را به منابع نسبت نده.

## ۷. منشأ و تعارض‌های اسناد محلی
منابع بازخوانی‌شده: Trading_Manager_Config.json، Trading_Manager_State.json، Trading_Workflow_Overrides.md، .skill-tools/rr2-native.py، پروتکل نسخه ۵ و اسکیل‌های تحلیل/پژوهش و operating-contract/prior-evidence.
Overrides هنوز نام نسخه ۴ دارد؛ config و پروتکل نسخه ۵ را مشخص می‌کنند.
اسکیل پایه از H1/M5، شکست/بازآزمایی، فیلتر خبر و قرارداد ریسک قدیمی حرف می‌زند؛ این‌ها نباید خودکار به مدل مومنتوم آخر افزوده شوند.
اعداد و دستورهای پیوست صرفاً برای انتقال دقیق سابقه‌اند؛ بخش توقف و محدوده آموزشی ابتدای فایل بر کاربرد این بسته حاکم است.

## پیوست A — متن اصلی اسکیل تحلیل (عین فایل؛ مرجع تاریخی)

---
name: mt5-market-analysis
description: "Analyze fresh broker market data and produce numerical MT5 demo trade candidates or explicit skip reasons. Use for market screening, structure and signal validation."
---

# mt5-market-analysis

Produce candidates, not orders. Read the shared contract at ../mt5-trading-manager/references/operating-contract.md. Load the current config and exact enabled version; use only actual tradable Market Watch symbols with contract metadata and valid history.

Normalize broker timestamps to UTC. Retrieve M5 setup history and closed H1 context; retrieve exact M1 after a qualifying retest, including the preceding M1. Validate ordering, gaps, OHLC, expected last closed candle and quote freshness. Inspect broker economic-calendar event details, currencies, importance and unknown-time markers. Unknown relevant timing blocks execution. Block relevant high-impact releases 15 minutes before to 15 minutes after; apply a management exit rule before a news block.

For the installed rolling experiment call ../mt5-trading-manager/scripts/evaluate.mjs through the manager CLI with a saved fresh snapshot. Its session start makes only newly completed setups eligible. Do not reuse the old FOMC anchor or failed continuation signals. H1 is context; describe opposing structure and abnormal volatility. A signal contains version, side, frozen level/ATR/buffer, setup/retest/trigger UTC, expiry, structural SL, 2R TP and dedup key. Candidate status is analysis_ready; execution must re-read account/quote and compute its own sizing. Log skip_code such as no_breakout, no_retest, exact_M1_missing, stale_signal, spread, abnormal_range or min_volume.

Return the analysis artifact path, candidate count, data timestamps and one decision reason per symbol. Do not rank solely by potential profit; prefer lowest cost/risk among equally valid independent signals.


## پیوست B — متن اصلی اسکیل پژوهش (مرجع تاریخی؛ مجوزهای قدیمی قابل انتقال نیستند)

---
name: mt5-trading-research
description: "Research primary financial sources and broker execution conditions, design frozen experiments and evaluate cost-aware improvements for MT5. Use for trading research and version proposals."
---

# mt5-trading-research

Read ../mt5-trading-manager/references/prior-evidence.md. Use BIS, central banks, CFTC and original academic papers for mechanisms; use native broker quotes/specifications/deals for executable conditions. Verify linked sources and their dates. Trading blogs may explain methods but cannot establish independent profitability.

Translate evidence into a falsifiable change in spread, liquidity, volatility, timing, quote age, latency, cost or sizing. Record which threshold is your hypothesis rather than a source recommendation. Log version, rationale, numerical rules, cost model, datasets/date splits, selection count, acceptance/rejection criteria and status. Preserve untouched chronological holdout; include conservative spread, fees, slippage, intrabar ambiguity, margin and risk halts.

Treat E:/GPT/Inves historical files as research artifacts. Do not re-enable rejected continuation/RSI versions, mix connectivity PnL with strategy results, or claim the untested SP2L descriptions are precise executable rules. Consult current manager rejection counts to choose research priorities. Fix demonstrated operational failures promptly; hold strategy changes until prospectively registered. The user's direct instruction on 2026-10-08 authorizes a 10% hard ceiling for total open price risk plus cost reserve. Active risk remains 1%; increases need the existing 12-hour/OOS conditions, must fit the 2% peak drawdown headroom, and must never use the ceiling as a target.

Return an immutable research proposal artifact with sources and criterion status. Manager may approve a capped prospective demo experiment while research_gate_passed=false; this must remain separate from validated strategy promotion. No research agent or helper submits orders.


## پیوست C — پروتکل عددی اصلی نسخه ۵ (JSON، داده تاریخی)

~~~json
{
  "id": "SEVEN_RR2_1791562871308",
  "version": "DEMO_7_SYMBOLS_RR2_NO_NEWS_5",
  "registeredUTC": "2026-10-09T18:11:16.676Z",
  "deadlineUTC": "2026-11-08T16:45:32.380Z",
  "target": 700,
  "scope": "explicit_user_seven_symbols",
  "catalogPath": "E:/GPT/Inves/trading-journal/native_all_symbols_catalog_20261009T160416913627Z.json",
  "catalogCount": 7,
  "userInstruction": "XAUUSD EURUSD GBPUSD USDJPY USDCHF USDCAD AUDUSD؛ روی این نمادها تست کن؛ نتیجه تفکیکی",
  "priorRoundArchive": "E:/GPT/Inves/trading-journal/prior_round_superseded_1791562339139.json",
  "interpretation": "تفسیر ایجنت؛ prospective unvalidated",
  "signal": {
    "windowSeconds": 5,
    "minimumAbsReturnTicks": 1,
    "minimumAbsReturnSpread": 0.5,
    "closedM1Alignment": true,
    "zeroReturn": "skip",
    "activationUTC": "2026-10-09T18:11:16.676Z"
  },
  "stops": {
    "structural": "last_two_closed_M1_extreme_plus_two_ticks; never tightened to fit volume",
    "minimumDistance": "max(0.5*ATR14,4*spread,(stop_level+2)*point,2*ticks)",
    "rewardRisk": 2,
    "basis": "native account-currency gross reward divided by native initial price risk; round target away by ticks",
    "actualFillDeviation": "Native actual RR is verified and reported; no SL/TP modification after fill."
  },
  "exits": "BROKER_SL_TP_ONLY_NO_MANUAL_CLOSE_NO_TRAILING",
  "volume": "broker_minimum_valid_step",
  "margin": "exact native per contract and side; available broker free margin",
  "costFilters": {
    "maxSpreadATR": 0.25,
    "maxScenarioReserveVsInitialRisk": 0.25,
    "slippageTicks": 2,
    "feeScenarioUSD": 0.07,
    "reserveMode": "report_only"
  },
  "news": "DISABLED_BY_DIRECT_USER_FOR_DEMO",
  "selection": "Rotate only the explicit seven symbols; one owned pending order or position per symbol; actual free margin plus pending margin reservation.",
  "primaryMetric": "per-symbol net-win count divided by all reconciled closes including flats; also TP-hit rate and Wilson interval",
  "sample": "100 reconciled actual exits per symbol,700 total; report separately by entry version; retain nonconforming fills transparently.",
  "guarantee": "none",
  "sources": [
    "https://www.mql5.com/en/docs/python_metatrader5/mt5ordercalcprofit_py",
    "https://www.mql5.com/en/docs/python_metatrader5/mt5ordercalcmargin_py"
  ],
  "symbols": [
    "XAUUSD",
    "EURUSD",
    "GBPUSD",
    "USDJPY",
    "USDCHF",
    "USDCAD",
    "AUDUSD"
  ],
  "priorUnfilledProtocol": "E:/GPT/Inves/.skill-tools/all-symbols-rr2-protocol_1791562339139.json",
  "targetPerSymbol": 100,
  "concurrency": "maximum one owned position per symbol; broker actual free margin applies",
  "targetAmendmentPath": "E:/GPT/Inves/trading-journal/seven_700_parallel_amendment_1791564332380.json",
  "priorProtocol": "E:/GPT/Inves/.skill-tools/seven-managed-limit-protocol_1791567274371.json",
  "entryOrderPolicy": "LIMIT_WITH_MANAGED_EXPIRY",
  "pendingValiditySeconds": 45,
  "amendmentPath": "E:/GPT/Inves/trading-journal/rr2_no_news_amendment_1791569476676.json",
  "pendingExpiry": "Active manager cancels unfilled owned order after45s; not broker enforced",
  "newsFilterEnabled": false
}
~~~

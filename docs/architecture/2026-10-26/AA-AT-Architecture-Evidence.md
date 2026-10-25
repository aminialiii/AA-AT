# AA-AT — شواهد معماری و ممیزی Git

تاریخ گردآوری: ۲۰۲۶-۱۰-۲۵، حدود ۲۳:۰۶ تا ۲۳:۱۰ UTC. `VERIFIED_RUNNING` در این سند فقط به مشاهدهٔ فرایند/task و heartbeat **در همان زمان** اشاره می‌کند. بروکر جداگانه در این مأموریت پرس‌وجو نشده و وضعیت بعدی از این جدول قابل استنتاج نیست. مبنای مسیرهای Git، worktree پژوهشی `research/v3-isolated-backtest` است؛ مسیرهای account-bound و نام کاربر/رایانه در سند درج نشده‌اند.

| جزء یا ارتباط | شاهد پیاده‌سازی | وضعیت پیاده‌سازی / عملیاتی در زمان مشاهده | وابستگی یا محدودیت |
|---|---|---|---|
| MT5 DEMO و گیت هویت | `research/demo-live-20261021/broker.py:27-64`، `service.py:595-655`؛ heartbeat محلی ۲۳:۰۵:۵۴ UTC | `IMPLEMENTED` / `VERIFIED_RUNNING` طبق heartbeat محلی؛ بدون پرس‌وجوی مستقل تازه | حساب پین‌شدهٔ DEMO، hedging، مجوز معامله، اتصال |
| دریافت M1 و زمان/قیمت | `broker.py:67-102`، `service.py:535-582` | `IMPLEMENTED` / جریان فعال فقط در heartbeat نمونه | تازه‌بودن quote و سازگاری ساعت؛ وقفه‌های قبلی ثبت شده‌اند |
| قواعد منجمد S01–S05 و سیگنال | `service.py:73-78,395-423`، `live_signals.py`، `research/overnight-20261010/engine.py` | `IMPLEMENTED` / پنج worker در heartbeat `ACTIVE` | ثبت‌های S06–S18 مسیر اجرایی قابل‌تأیید ندارند |
| S06–S18 | `research_outputs/inventory.json`، `research/v3/status.py:35-57` | `BLOCKED` / سیزده worker در heartbeat `BLOCKED` | پیاده‌سازی و وابستگی اجرای کامل غایب |
| ناظر ریسک و قفل پذیرش | `research/demo-live-20261021/portfolio_policy.py:42-69,100-150` و `service.py:303-360` | `IMPLEMENTED` / hash سیاست مؤثر v4 در heartbeat مطابق فایل | موقعیت، سفارش معلق و intent رزروشده در ظرفیت/ریسک محاسبه می‌شوند |
| گیت ارسال و تطبیق | `broker.py:27-64,145-178`، `service.py:173-225,303-394` | `IMPLEMENTED` / وضعیت ارسال فعلی `UNKNOWN`؛ سفارش آزمایشی اجرا نشد | هویت DEMO و exposure دوباره پیش از ارسال، تطبیق پس از fill |
| دفترکل و شواهد بروکر | `state.py:17-100`، `service.py:173-225,459-481`؛ heartbeat محلی | `IMPLEMENTED` / ۳۹۵ معاملهٔ بسته در snapshot؛ صحت فعلی نیازمند تطبیق تازه | SQLite و فایل‌های evidence عملیاتی؛ در Git نیستند |
| توقف اضطراری و breaker | `service.py:34,94-100,303-306,582-590,635-650` | `IMPLEMENTED` / فایل توقف در ۲۳:۰۶ UTC غایب؛ breaker هر کارگر باید جدا خوانده شود | نبود marker به‌تنهایی مجوز معامله نیست |
| Command Center، `:8765` | `command_center/server.py:39,94-160,174-247`، `telemetry.py:139-229`؛ listener محلی | `VERIFIED_RUNNING` برای listener؛ تله‌متری زمان‌دار | loopback و احراز هویت؛ هیچ درخواست کنترلی در این ممیزی ارسال نشد |
| پل کنترل کارگران | `command_center/server.py:275-330`، `telemetry.py:203-205`؛ `control_bridge_version` در heartbeat تهی | `IMPLEMENTED_NOT_RUNNING` / مسیر اجرای command تأیید نشده | API در صورت نبود پل پاسخ `503` می‌دهد |
| Graphify | `graphify-out/graph.json` و `validation.json` | `IMPLEMENTED_NOT_RUNNING`؛ artifact ایستا، ۳۰۴ گره/۸۱۴ یال، snapshot ۲۳ اکتبر | برای risk v4 به‌روز نیست؛ منبع مقادیر مؤثر محسوب نشد |
| گردآورنده → انبار پژوهش | `research/trade_forensics/collector.py:1-90`، `store.py`؛ `collector-status.json` ۲۳:۰۸:۵۵ UTC | `VERIFIED_RUNNING` برای task و heartbeat پژوهش؛ ۳۹۵ ردیف، صفر candle/tick | فقط خواندن شواهد عملیاتی و نوشتن به store جدا؛ MT5 import نمی‌کند |
| API پژوهشی Command Center | `command_center/research_api.py:27-38,53-176`، `server.py:204-245` | `IMPLEMENTED` / read-only SQLite و گزارش‌های نسخه‌دار | دادهٔ تحلیلی مستقل از مسیر سفارش |
| داشبورد پژوهش `:8775` | `research/v3/dashboard.py:45-88`، `status.py:1-100`؛ listener محلی | `VERIFIED_RUNNING` برای listener | توکن پژوهشی؛ status پژوهشی، نه PnL حساب DEMO |
| دادهٔ تاریخی و انبار v3 | `research/v3/market_import.py`، `research/v3/status.py:15-100`؛ checkpoint v3 | `RESEARCH_ONLY`؛ هشت منبع جزئی، ۶۶۵٬۰۰۰ ردیف M1 گزارش‌شده؛ صفر منبع واجد پوشش سه‌ساله | UTC برخی آرشیوها تأیید نشده؛ XAUUSD معتبر غایب |
| EA پژوهشی S04 و parity | `research/v3/parity_runtime.py:25-168`، `research/v3/parity_dataset.py:40-113`؛ checkpoint v3 | `RESEARCH_ONLY`؛ کامپایل v2 موفق؛ runtime parity `NOT_TESTED` | trace واقعی Strategy Tester غایب |
| MT5 Strategy Tester مستقل | `research/v3/status.py:88-100`، `tester-probe-analysis.json` | `BLOCKED`؛ ترمینال جدا بالا آمده و خارج شده، tester با `ACCOUNT_NOT_SPECIFIED` اجرا نشد | حساب پژوهشی مستقل لازم است؛ استفاده از MT5 عملیاتی ممنوع |
| Market Status Engine | `research/v3/market_status.py:24-80`، `status.py:76-90` | `RESEARCH_ONLY`؛ منبع برنامهٔ نشست بروکر تأیید نشده | وضعیت `UNKNOWN` نباید از quote کهنه به closure تبدیل شود |
| Economic Calendar | `research/v3/economic_calendar.py:17-88`، `status.py:95-100` | `RESEARCH_ONLY`؛ صفر رویداد معتبر در dashboard checkpoint | منبع تاریخی/بازنگری‌شده وصل نشده |
| پشتیبان V1/V2/V3 | `tools/backup_worker.py:166-182,232-309,315-354`؛ `backup-status.json` | `VERIFIED_RUNNING`؛ V2 در ۲۲:۵۸:۳۹ UTC موفق، heartbeat ۲۳:۰۹:۴۰ UTC | آرشیوها بیرون Git؛ در این مأموریت خوانده شدند، تغییری نکردند |
| Git sync چهار ساعته | `tools/sync_worker.py:22-29,79-116,160-231`؛ Task Scheduler و `AA-AT-sync-state/status.json` | `IMPLEMENTED`؛ آخرین اجرا ۱۹:۵۰ UTC، exit 0، `NO_CHANGE` | فقط `automation/source-sync` را push می‌کند؛ `main` را merge نمی‌کند |

ارجاع‌های `research/demo-live-20261021/*` در سطرهای معاملاتی به **نسخهٔ محلیِ محافظت‌شده و جاری** اشاره دارند؛ branch پژوهش v3 یک نسخهٔ قدیمی‌تر از سیاست ریسک دارد. نسخهٔ v4 در شاخهٔ جداگانهٔ `research/gold-demo-admission` با commit `5e08166...` موجود است و hash فایل محلی سیاست با heartbeat تطبیق داده شد. از Graphify قدیمی برای ادعای جریان جاری استفاده نشد.

## سیاست مؤثر و اختلاف اسناد

`risk_policy.json:1-11` در نسخهٔ عملیاتی، `policy_version=4`، پنج جایگاه، `max_open_fraction=0.10`، توقف زیان روزانه `0.05`، افت قله `0.10` و ادامه پس از ۱۰۰ معامله را ثبت می‌کند. `portfolio_policy.py:108-119` سقف طلا را به کمینهٔ ۱۰ دلار، ۱٪ اکوئیتی و headroom محدود می‌کند. `service.py:303-360` از قفل route، انقضای سیگنال و intent پایدار استفاده می‌کند. بنابراین درخواست نمودار با عدد ۲٪ و مستندات قدیمی که ۲٪ را تکرار می‌کنند با وضعیت مؤثر ناسازگارند. LLD مقدار ۱۰٪ فعلی را نشان می‌دهد. این ممیزی هیچ پارامتری را تغییر نداده است.

## ممیزی GitHub و علت تاریخ قدیمیِ قابل‌مشاهده

Remote پیکربندی‌شده `origin` به مخزن خصوصی `AA-AT` اشاره می‌کند. شاخهٔ پیش‌فرض محلی و ref ردیابی‌شدهٔ `origin/main` روی `eccbec8fec62443d60a5a23a5c093c85d4da78d2` (commit در ۲۰۲۶-۱۰-۲۱ ۲۳:۴۰:۴۶ UTC) هستند؛ به همین دلیل صفحهٔ پیش‌فرض می‌تواند «حدود چهار روز قبل» نشان دهد. شاخهٔ پژوهش `research/v3-isolated-backtest` در worktree تمیز، روی `6f2602d58f03fb4b64acf94670387b50d364642c` (۲۰۲۶-۱۰-۲۵ ۱۷:۱۰:۰۳ UTC) بود. شاخهٔ جداگانهٔ gold/risk روی `5e0816673d0ba3a7fd19bd0b8e39ed0f4dcc9d8b` (۲۰۲۶-۱۰-۲۵ ۲۲:۵۸:۳۸ UTC) است. این‌ها به `main` merge نشده‌اند.

Task `AAATGitHubSync4h` در ۲۰۲۶-۱۰-۲۵ ۱۹:۵۰:۰۴ UTC با exit 0 اجرا شده و status خود را `NO_CHANGE`، ۲۵۷ فایل بررسی‌شده و صفر تغییر معنی‌دار ثبت کرده است؛ اجرای بعدی برای ۲۳:۵۰:۰۳ UTC برنامه‌ریزی شده بود. Sync کد فقط روی `automation/source-sync` push می‌کند و PR بازبینی می‌سازد. آخرین push موفق **طبق status محلی** `46c4f00eca4a2d72909935739c81a09612a9cad7` است؛ ref ردیابی‌شدهٔ محلی آن شاخه `795f656...` است و ممکن است از remote عقب باشد، زیرا fetch تازه انجام نشده است. بنابراین آن ref را remote HEAD قطعی نمی‌نامیم.

در نخستین تلاشِ ۲۳:۰۶ UTC، `git ls-remote` به‌علت خطای موقت اتصال به GitHub:443 شکست خورد؛ تلاش بعدی موفق شد. `HEAD` راه‌دور روی `main`، `eccbec8...`، روی `research/v3-isolated-backtest`، `6f2602d...`، روی `research/gold-demo-admission`، `5e08166...` و روی `automation/source-sync`، `46c4f00...` را تأیید کرد. در نتیجه شاخهٔ پیش‌فرض قدیمی است ولی pushهای پژوهشی موجودند؛ آخرین push موفق worker طبق audit محلی در ۲۰۲۶-۱۰-۲۴ ۰۷:۵۰:۲۲ UTC بوده است. کانکتور GitHub برای این مخزن خصوصی HTTP 404 برگرداند، پس حفاظت شاخه و مجوز API از این مسیر قابل‌تأیید نبود؛ دسترسی خواندن Git remote برقرار است. checkout اصلی تغییرات محلی محافظت‌شده داشت و در این مأموریت دست‌کاری نشد. هیچ تغییر در منطق sync یا task عملیاتی انجام نشد. انتشار نمودارها پس از push جدید جداگانه راستی‌آزمایی می‌شود.

## مقایسهٔ یکپارچگی تولید، پیش و پس از مستندسازی

دو نمونهٔ فقط‌خواندنی در ۲۳:۰۶:۵۱ و ۲۳:۱۴:۳۸ UTC گرفته شد. hash و زمان ویرایش شش فایل حفاظت‌شده، شامل منبع منجمد، پیکربندی account-bound، سیاست ریسک، سرویس، adapter بروکر و ناظر پرتفوی **همگی MATCH** بودند. نمونه‌های شاخص:

| مورد | پیش | پس | نتیجه |
|---|---|---|---|
| منبع منجمد `engine.py` | `7858325bc531...` | `7858325bc531...` | MATCH |
| پیکربندی campaign | `090df89016b4...` | `090df89016b4...` | MATCH؛ محتوا منتشر نشد |
| سیاست مؤثر v4 | `f28283ff6ce2...` | `f28283ff6ce2...` | MATCH |
| تعریف task معاملاتی | `8a3e91b64d07...` | `8a3e91b64d07...` | MATCH؛ هر دو `Running` |
| marker توقف اضطراری | غایب | غایب | MATCH؛ marker دست‌کاری نشد |
| heartbeat | زمان فایل پیش ۲۳:۰۶:۵۰ UTC | بعد ۲۳:۱۴:۳۸ UTC | سرویس مستقل به‌روزرسانی شد |

باینری ترمینال عملیاتی از مسیر موجود در پیکربندی account-bound به‌صورت خواندنی hash شد؛ مقدار مشاهده‌شده `dd070886d6a0...` بود. hash پیکربندی campaign که مسیر MT5 را تعیین می‌کند پیش/پس تغییر نکرد. شمار بسته‌ها در heartbeat بعدی همچنان ۳۹۵، پنج worker فعال و سیزده worker مسدود بود؛ این، جایگزین بررسی مستقلِ همهٔ رکوردهای بروکر یا hash پایگاهِ درحال‌نوشتن نیست. هیچ task، worker، dashboard عملیاتی، terminal یا ledger توسط این کار متوقف، restart یا ویرایش نشد.

## حریم خصوصی و حدود شواهد

مستندات جدید نام حساب، نام کاربر/رایانه، مسیر home و کلید را ثبت نمی‌کنند. هشت سند tracked قدیمیِ همین شاخهٔ پژوهشی که نام کاربر OS داشتند با `%USERPROFILE%` ماسک شدند. تاریخچهٔ Git بازنویسی نمی‌شود و شاخهٔ پیش‌فرض بدون merge یا مجوز تغییر نمی‌کند. جست‌وجوی tracked-file هنوز **۱۶ فایل کد/اسکریپت** با همان شناسهٔ سیستم نشان داد؛ آن‌ها به‌سبب قانون صفر تغییر در کد عملیاتی و محدودیت دامنهٔ این مأموریت دست‌نخورده‌اند. پاک‌سازی آن‌ها نیازمند بازبینی جداگانهٔ مالکیت فایل و اثر بر مسیرهای اجرایی است. نبود فایل مرجع اینفوگرافیک قدیمی، تطبیق دقیق سبک را محدود می‌کند؛ الگوی رنگ و چیدمان طبق متن درخواست پیاده شد.

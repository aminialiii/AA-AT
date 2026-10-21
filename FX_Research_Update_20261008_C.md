# پژوهش عملیاتی C — حجم‌گذاری داینامیک و هزینهٔ اجرا

## منابع و نتیجهٔ قابل‌اجرا

- [BIS Working Paper 1073](https://www.bis.org/publications/working-paper-1073-constrained-liquidity-provision-currency-markets) نشان می‌دهد وقتی ظرفیت واسطه‌ها محدود می‌شود، هزینهٔ نقدشوندگی نامتناسب بالا می‌رود. نتیجهٔ عملی: حجم فقط از ریسک حدضرر محاسبه نمی‌شود؛ اسپرد تازه، هزینهٔ ثابت و شواهد margin باید داخل بودجه بماند و حدضرر ساختاری نباید برای جا دادن حجم تنگ شود.
- [BIS Working Paper 629](https://www.bis.org/publications/working-paper-629-beneficial-aspect-fx-volatility-market-liquidity) گزارش می‌کند نوسان در سطوح بسیار بالا با افت فعالیت نقدشوندگی همراه می‌شود. نتیجهٔ عملی: افزایش تعداد فرصت‌ها با عبور از فیلتر اسپرد/کندل غیرعادی مجاز نیست؛ در جهش غیرعادی، سیگنال حذف می‌شود.
- [BIS Working Paper 249](https://www.bis.org/publications/working-paper-249-frequency-observation-and-estimation-integrated-volatility-deep-and-liquid-financial-markets) نشان می‌دهد فراوانی مشاهده برای برآورد نوسان با نویز خردساختار محدود می‌شود و در روزهای خبر رفتار متفاوت است. نتیجهٔ عملی: M5 برای غربال، M1 فقط برای تأیید prescribed، و quote تازه پیش از سفارش باقی می‌ماند.
- [CFTC retail forex rules Q&A](https://www.cftc.gov/sites/default/files/idc/groups/public/@newsroom/documents/file/forexfinalrule_qa.pdf) و [هشدار ریسک اهرم](https://www.cftc.gov/sites/default/files/idc/groups/public/@newsroom/documents/file/forexrulesproposal.pdf) ریسک اهرم و زیان سریع را برجسته می‌کنند. نتیجهٔ عملی: hard ceiling پنج درصد مقدار هدف نیست؛ مقدار فعال یک درصد می‌ماند تا معیار خارج‌نمونه تکمیل شود.
- [Target volatility strategies: optimal rebalancing boundary for transaction cost minimization](https://doi.org/10.1007/s11408-025-00486-5) نقش هزینهٔ معامله را در کاهش گردش و اندازهٔ موقعیت نشان می‌دهد. نتیجهٔ عملی: حجم بر اساس بودجهٔ خالص پس از ذخیرهٔ هزینه و گرد کردن به گام قرارداد محاسبه می‌شود؛ حجم حداقل که در بودجه جا نشود، رد می‌شود.

## تغییر ثبت‌شده

نسخهٔ prospective `US_FOMC_RANGE_RETEST_DYNAMIC_RISK_1` در `Demo_Entry_Rules_20261008_DYNAMIC.json` ثبت شد. الگوی ورود، حدضرر ساختاری، TP، خبر و dedup از نسخهٔ قبلی به ارث می‌رسد. سقف ورود از ۲ به ۴ افزایش یافته ولی هم‌زمان فقط یک پوزیشن مجاز است. حجم ثابت ۰٫۰۱ با فرمول contract-aware جایگزین شده؛ ریسک فعال ۱٪، hard ceiling پنج درصد و توقف افت دو درصد بدون تغییر است.

## فرضیه و معیار پذیرش

فرضیه این است که حجم‌گذاری بر مبنای فاصلهٔ واقعی SL، گام قرارداد و هزینه، بخشی از skipهای ناشی از حداقل حجم ثابت را کم می‌کند بدون اینکه زیان مجاز هر معامله از بودجه عبور کند. فعال‌سازی افزایش ریسک منوط به حداقل ۲۰ معاملهٔ بستهٔ خارج‌نمونه، سود خالص پس از هزینه، PF حداقل ۱٫۱ و افت مشاهده‌شده زیر دو درصد است. نسخه فعلاً آزمون‌نشده است.

## checkpoint چرخهٔ 2026-10-08T11:25Z

- [BIS Triennial 2025 execution landscape](https://www.bis.org/publications/qr-202512/fx-trade-execution-landscape-through-prism-2025-bis-triennial-survey) بر OTC و پراکندگی نقدشوندگی تأکید می‌کند؛ بنابراین برای اجرای دمو، spread و quote تازه باید در همان لحظهٔ سفارش دوباره خوانده شوند و نماد با quote قدیمی یا جهش spread رد شود.
- [CFTC risk-controls concept release](https://www.cftc.gov/PressRoom/PressReleases/6683-13) کنترل‌های پیش‌معامله، گزارش پس‌معامله و safeguards را جدا می‌کند؛ بنابراین dedup، سقف حجم، سقف ورود، ثبت intent پیش از سفارش و تطبیق fill/SL/TP پس از سفارش حفظ شد.
- این پژوهش هیچ پارامتر معاملاتی را تغییر نداد. فرضیهٔ بعدی: در اولین رویداد تازه، نرخ رد شدن هر نماد را جداگانه با علت `spread`, `stale_quote`, `margin_unknown`, `min_volume` و `structural_stop` ثبت کنیم و بعد از حداقل 20 معامله بررسی کنیم که رد شدن‌ها واقعاً ریسک و هزینه را کم کرده‌اند.
- وضعیت آزمون: prospective و آزمون‌نشده؛ sample مؤثر همچنان 1 معاملهٔ تست اتصال است.

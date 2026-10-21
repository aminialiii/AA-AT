# گزارش بهینه‌سازی ۱۰ چرخه

تاریخ: 2026-10-09T12:32:45.227Z
بک‌تست تاریخی: E:/GPT/Inves/research/poursamadi-backtest/backtest_result_20261009T123229348228Z.json
تعداد کندل: 29036
تعداد setup: 6
شبیه‌سازی معتبر: 2
gate نهایی: رد شده

## جدول چرخه‌ها
|چرخه|مرحله|Train|Validation|Test|وضعیت|
|---:|---|---:|---:|---:|---|
|1|initial audit|0|0|0|REJECTED_INSUFFICIENT_OOS|
|2|apply time filter|0|0|0|REJECTED_INSUFFICIENT_OOS|
|3|retest quality|0|0|0|REJECTED_INSUFFICIENT_OOS|
|4|entry filter validation|0|0|0|REJECTED_INSUFFICIENT_OOS|
|5|session optimization|0|0|0|REJECTED_INSUFFICIENT_OOS|
|6|signal quality|0|0|0|REJECTED_INSUFFICIENT_OOS|
|7|TP/SL grid|0|0|0|REJECTED_INSUFFICIENT_OOS|
|8|regime stability|0|0|0|REJECTED_INSUFFICIENT_OOS|
|9|walk-forward validation|0|0|0|REJECTED_INSUFFICIENT_OOS|
|10|final selection|0|0|0|REJECTED_INSUFFICIENT_OOS|

## ممیزی ۱۰۰ معاملهٔ دمو
```json
{
  "N": 100,
  "netUSD": -0.79,
  "PF": 0.5353,
  "expectancyUSD": -0.0079,
  "winRate": 29,
  "maxDD": 0.008866
}
```
این بخش اجرای دمو را توصیف می‌کند و جایگزین آزمون تاریخی خارج‌نمونه نیست.

## نتیجه
- هیچ نسخه‌ای به‌دلیل نبود نمونهٔ مستقل ارتقا نیافت.
- تغییر زمان، ورود یا TP/SL بر اساس این داده‌ها قابل دفاع نیست.
- دادهٔ آزمون نهایی دست‌نخورده نگه داشته شد.
- برای ادامه، باید archive تاریخی M1/tick با پوشش train/validation/test و حداقل ۳۰ معامله در test فراهم شود.

نمودار: E:/GPT/Inves/research/poursamadi-backtest/equity_curve_demo_100_1791549165224.svg
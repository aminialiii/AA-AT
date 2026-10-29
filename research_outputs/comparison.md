# Measured baseline versus candidates

No confirmed improvement. This table follows the validation-frozen order; historical test outcomes were not used to reorder it. All results are offline OHLC approximations on already-exposed archives.

|Strategy/candidate|Symbol/TF|Validation N|Validation E_R baseline → candidate|Historical test N|Test E_R baseline → candidate|Test net USD baseline → candidate|Verdict|
|---|---|---:|---:|---:|---:|---:|---|
|S01 / PRICE_ACTION_CONFIRMATION|XAUUSD / M1|55|0.220 → 0.328|53|0.168 → 0.038|17.36 → -1.84|NO_CONFIRMED_IMPROVEMENT|
|S02 / TIME_FILTER|XAUUSD / M1|78|-0.116 → 0.166|87|0.007 → -0.028|-36.39 → -23.60|NO_CONFIRMED_IMPROVEMENT|
|S04 / TIME_FILTER|XAUUSD / M1|199|-0.190 → -0.109|133|-0.079 → -0.078|27.23 → 17.02|NO_CONFIRMED_IMPROVEMENT|
|S03 / RISK_EXECUTION_REFINEMENT|XAUUSD / M1|137|-0.273 → -0.161|140|-0.184 → -0.144|-81.27 → -2.01|NO_CONFIRMED_IMPROVEMENT|
|S05 / PRICE_ACTION_CONFIRMATION|USDCHF / M1|1|1.640 → 1.640|0|— → —|0.00 → 0.00|INCONCLUSIVE_SMALL_SAMPLE|

E_R is equal-weight net R/trade; netUSD uses fixed broker-minimum volume and variable stop risk. Their signs can differ; R profit factor is not dollar profit factor. See dollar_accounting.csv. No untouched OOS was available; NOT_RUN entries for S06-S18 and COMBINED are in complete CSV tables and dossiers.

Primary comparisons:224; historical prior search:448. Paired10,000-day-block bootstrap tests use Bonferroni across224 current comparisons. Only S01/XAU/M1/PRICE_ACTION_CONFIRMATION passes that exploratory validation uplift gate (adjusted p≈.0224), then weakens from baseline .1675R to.0375R on historical test and becomes negative under cost stress. No production conclusion follows from validation significance.

S02 time filter has positive validation expectancy but negative historical test expectancy. S03/S04 remain negative-expectancy diagnostics; S05 nomination has one validation trade and zero test trades. No case had two qualifying independent ablations, so COMBINED was NOT_RUN.

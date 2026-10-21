# PROVISIONAL options — USER_DECISION_GATE

No candidate has enough evidence for production, demo, live or paper activation. The five nominations below were ranked on validation only, one per implemented family; failed and sparse nominations remain visible rather than being replaced using historical test outcomes.

|Strategy/candidate|Symbol/TF|Validation N|Validation E_R baseline → candidate|Historical test N|Test E_R baseline → candidate|Test net USD baseline → candidate|Verdict|
|---|---|---:|---:|---:|---:|---:|---|
|S01 / PRICE_ACTION_CONFIRMATION|XAUUSD / M1|55|0.220 → 0.328|53|0.168 → 0.038|17.36 → -1.84|NO_CONFIRMED_IMPROVEMENT|
|S02 / TIME_FILTER|XAUUSD / M1|78|-0.116 → 0.166|87|0.007 → -0.028|-36.39 → -23.60|NO_CONFIRMED_IMPROVEMENT|
|S04 / TIME_FILTER|XAUUSD / M1|199|-0.190 → -0.109|133|-0.079 → -0.078|27.23 → 17.02|NO_CONFIRMED_IMPROVEMENT|
|S03 / RISK_EXECUTION_REFINEMENT|XAUUSD / M1|137|-0.273 → -0.161|140|-0.184 → -0.144|-81.27 → -2.01|NO_CONFIRMED_IMPROVEMENT|
|S05 / PRICE_ACTION_CONFIRMATION|USDCHF / M1|1|1.640 → 1.640|0|— → —|0.00 → 0.00|INCONCLUSIVE_SMALL_SAMPLE|

1. **S01 + PRICE_ACTION_CONFIRMATION:** clearest measured validation uplift; historical test and cost/latency sensitivity undermine it. Suitable only for a new frozen offline validation proposal. Keep S01 + BASELINE as the mandatory unchanged comparator.
2. **S02 + TIME_FILTER:** explicit timezone-aware hypothesis and adequate samples, but no positive historical-test expectancy or multiplicity-supported uplift. Lower-priority offline hypothesis.
3. **S04 + TIME_FILTER:** simpler comparator with ample samples; negative expectancy means no improvement claim. Useful as a rejection/control study only.
4. **S03 + RISK_EXECUTION_REFINEMENT:** narrower cost/volatility eligibility reduces modeled losses but remains negative; defer integration.
5. **S05 + PRICE_ACTION_CONFIRMATION:** insufficient sample (one validation trade, zero test trades); investigate specification/data coverage before further parameter search.

Recommendation PROVISIONAL: retain original baselines; if choosing further work, start with S01 + PRICE_ACTION_CONFIRMATION against S01 + BASELINE on genuinely unexposed data. This is not a final strategy winner.

Choose a strategy ID + candidate ID for the next offline research step. Any production integration or trading activation requires a separate explicit instruction.

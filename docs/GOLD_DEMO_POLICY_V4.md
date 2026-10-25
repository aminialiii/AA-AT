# DEMO gold admission policy v4

This release is limited to the verified MetaQuotes DEMO campaign. It does not
change frozen S01–S05 signal rules, stop placement, the minimum broker volume,
five global position slots, one position per strategy, or one position per
symbol. It never authorizes REAL trading or manual signal generation.

## User-authorized bounds

| Control | Before | Version 4 |
| --- | ---: | ---: |
| XAUUSD planned risk per order, including cost reserve | 0.25% of the worker's virtual allocation | The actual 0.01-lot signal risk, capped at the least of USD 10, 1% of current account equity, remaining daily-loss headroom, and remaining peak-drawdown headroom |
| Other symbols' planned risk per order | 0.25% of worker allocation | Unchanged |
| Aggregate open and pending risk | 2% of account equity | 10% |
| Daily equity-loss halt | 1% | 5% |
| Peak-equity drawdown halt | 2% | 10% |
| Global position slots | 5 | Unchanged |

The gold ceiling is not a sizing target. The broker minimum lot remains 0.01;
signals whose structural stop plus conservative spread, commission, and
fill-deviation reserve exceed the ceiling are rejected. The existing margin,
fresh-quote, DEMO identity, same-symbol, duplicate-intent, atomic portfolio
admission, and post-fill breach checks remain mandatory. A fill beyond its
permitted deviation can still trip the worker breaker with broker SL/TP left in
place for reconciliation.

On 2026-10-26, the pre-change ledger held 395 broker-reconciled closes and no
XAUUSD closes. Of 202 recorded gold minimum-lot risk skips, the planned risks
ranged from USD 1.74 to USD 15.64 (median USD 4.245). This is historical
admission evidence, not a backtest or a prediction of new fills. The gold
strategy family has not passed independent three-year validation. Only fresh,
genuine signals can produce DEMO orders after a verified release.

## Release and rollback gates

1. Verify a fresh transactional backup and immutable source/config hashes.
2. Reconcile the pinned DEMO account, all positions/orders, prepared intents,
   safety events, emergency stop, quote freshness, and margin mode.
3. Run offline unit tests, static compilation, and secret scanning. Do not use
   synthetic fills in the campaign ledger.
4. Apply only the policy module, policy JSON, and service admission change.
   Preserve the original account-bound campaign configuration and source hash.
5. Restart the scheduled DEMO service only from a flat, reconciled state.
   Recheck the broker immediately after startup. If startup fails, keep routing
   stopped and restore the previous source/policy files from the local rollback
   copy only after reconciling broker state again.

An active worker is not proof of a gold trade. Count only broker-confirmed,
fully reconciled DEMO fills and closes.

# XAUUSD frozen-baseline compatibility gate

`COMPATIBLE` requires a faithful runnable baseline plus verified gold contract,
historical spread, stops, margin, sizing and out-of-sample evidence. No
strategy has cleared that gate. This table assesses existing source rules,
not a proposed gold deployment.

| IDs | Gold in frozen configured or documented scope | Current classification | Blocking evidence |
|---|---|---|---|
| S01–S05 | Seven-symbol configuration includes XAUUSD | INSUFFICIENT_INFORMATION | Only partial M1 source data; no full tick/UTC/cost/contract coverage or tester parity. S05 is a numerical proxy, not exact SP2L. |
| S06 | Seven-symbol native tick scanner includes XAUUSD | INSUFFICIENT_INFORMATION | Managed-limit and continuous tick replay missing. |
| S07–S08 | Gold-oriented rules | INSUFFICIENT_INFORMATION | Native or short-bar version dependencies incomplete. |
| S09 | Event-range evaluator includes XAUUSD | INSUFFICIENT_INFORMATION | Historical event anchors and state replay missing. |
| S10–S12 | Frozen configuration is EURUSD/GBPUSD only | INCOMPATIBLE with frozen gold baseline | Gold would require a separately versioned adaptation; the prepared indicator pipeline is also missing. |
| S13–S14 | Protocol-selected symbols | INSUFFICIENT_INFORMATION | Gold selection, tick history and exit-policy version not verified. |
| S15 | Configuration-selected symbols | INSUFFICIENT_INFORMATION | Frozen gold selection and installed evaluator dependencies not verified. |
| S16–S18 | Gold appears in proposals | INSUFFICIENT_INFORMATION | Mechanical rules remain incomplete; proposals are not executable baselines. |

No XAUUSD DEMO activation is authorized by V3. Any future activation requires
a separate explicit confirmation after independent tester and broker-specific
validation, and must not change frozen S01–S18 files.

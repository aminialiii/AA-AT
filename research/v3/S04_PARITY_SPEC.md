# S04 research parity contract

This specification describes the frozen S04 path; it does not change the
operational worker. Frozen source SHA-256:
`7858325bc531382b52bdb9e5fdc910b44cf7ebfe6bea19934e24faafd618ebfb`.
The research EA is a separate, versioned historical-test implementation.
The previous research v1 source is preserved; these corrections are in
`S04_MomentumProxy_v2.mq5`.

| Stage | Operational evidence | Required research comparison |
|---|---|---|
| Data | `research/demo-live-20261021/broker.py:97-101` requests up to 500 M1 rates. `live_signals.py:30-41` requires at least 260, removes the forming bar, and requires the last completed bar to be adjacent. | The EA requests at most 499 completed bars, requires 259, and evaluates on the first tick of the next forming minute. Compare bar timestamps, broker-to-UTC offset, OHLC, and spread points. |
| Signal | `research/overnight-20261010/engine.py:69-108`, model `OR1_40091e532162`: 14-bar arithmetic true-range mean floored at tick size; long when `(close-open)/ATR >= 0.2` and `close > previous close`; short when ratio `<= -0.2` and `close < previous close`. First 100 bars and 100 after each gap are invalid. Session `ALL`. | Compare every warmed, contiguous completed bar, including zero signals, ATR, side, and timestamp. |
| Quote gate | `research/demo-live-20261021/service.py:245-258`: **current** Bid/Ask spread divided by ATR must be at most 0.25. | Compare first eligible forming-bar tick and live spread. The previous-five-bar modeled spread is diagnostic only for this live gate. |
| Initial levels | `service.py:259-269`: minimum stop distance is max(0.5 ATR, 4 current spreads, broker stop level); long SL is below the last three lows by two ticks, short SL above the last three highs by current spread plus two ticks; round outward to the tick. The target is broker-native gross 2R. | Compare entry, SL, TP, minimum volume and native loss separately. The EA's `AAAT_V3_LEVELS` trace can be produced in `InpSignalOnly` mode. |
| Admission | `service.py:270-359` adds cost reserve, worst-fill risk, allocated-equity and margin checks, FOK availability, account and broker reconciliation, age, breaker, one-per-strategy, same-symbol, five-slot, and 2% portfolio gates. | **Not yet ported to the standalone EA.** Its tester trade journal cannot be called a faithful operational execution baseline until these gates or an equivalent research event model are validated. |
| Exit | `service.py:245-298` sends initial SL and TP. The frozen M1 replay in `engine.py:120-160` assumes bar-based SL/TP, with conservative same-bar collision handling and scenario costs. | No implemented S04 break-even, trailing, scale-out, or time-exit transition was found in this path. Tester fills, stop/target order, commissions and swap require separate validation; M1 replay is not broker-fill evidence. |

The research EA is tester-only, refuses a non-DEMO account classification, and
defaults to signal-only mode. Compilation and Python-rule checks do not establish
runtime parity. The runtime comparator requires source-hashed Bid/Ask ticks,
at least 260 contiguous M1 bars, a verified tester clock mapping, and an
actual MQL tester trace. The one accepted EURUSD tick hour contains only 60
minutes; therefore runtime parity and historical backtest counts remain zero.

The research dataset builder records raw source hashes and deliberately marks
its output ineligible for backtesting until the tester's bar construction,
clock mapping, contract specifications and execution costs are verified.
Historical simulated trades must use `HISTORICAL_BACKTEST`, never the
broker-confirmed DEMO ledger.

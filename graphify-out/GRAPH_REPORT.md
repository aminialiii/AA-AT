# Graphify development graph

This is an account-free development graph version. The full prior and live operational graph versions remain local in the original workspace. The graph covers selected trading, control-plane, and reporting Python files, the dashboard shell, and a broker-ledger-checked status snapshot; it does not claim complete repository coverage.

Nodes: 316. Directed relationships: 832. EXTRACTED 831, INFERRED 1, AMBIGUOUS 0.
Validation: no duplicate identities, missing endpoints, or unmatched source-line evidence.
Static imports and calls are references, not proof of runtime calls or data flow. Status edges are timestamped observations only. JSON preserves direction and parallel relationship types; HTML may visually overlap edges.
Broker order/deal records remain outside Git. No trade is inferred from strategy registration or source code.
The local command center serves a live authenticated telemetry projection. An API or control edge in this graph is not evidence that the runtime bridge is deployed or healthy; consult the timestamped local status and control audit.
The repository policy file is v5 with a 10% aggregate cap; the separate timestamped runtime snapshot reports 10%. This graph preserves both facts and does not treat the checked-in copy as effective runtime configuration.
The completed-candle adapter invalidates 100 M1 bars after a data gap. The frozen signal function zeros these invalid bars. This includes the weekend reopening gap and is a signal-validity rule, not a broker or portfolio-risk rejection.

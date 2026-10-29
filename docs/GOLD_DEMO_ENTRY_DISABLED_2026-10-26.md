# XAUUSD removed from new DEMO entries — 2026-10-26

The user withdrew XAUUSD from live DEMO trading. This change affects new entries only. The frozen strategy source, campaign configuration hash, existing risk limits, broker credentials, and order history were not changed.

The existing DEMO task had stopped with result `0xC000013A` and no campaign process. Its interruption source was not independently identifiable. Before deployment, a read-only broker preflight verified the pinned DEMO account, permissions, hedging, and zero open/pending positions. The campaign database passed integrity checks with 473 closed trades and one `OPEN` local USDCAD intent. Broker deal and order history proved that position was fully closed, and startup reconciliation recorded it without submitting an order.

The V3 pre-change backup was verified: SHA-256 matched, ZIP integrity passed, and a campaign database snapshot was present with 473 closes. The old broker adapter is retained in the separate deploy-backup directory for rollback. The new adapter removes XAUUSD from the six-symbol dispatch tuple and rejects any non-allowed symbol before `mt5.order_send`. It retains read-only symbol lookup for reconciliation of any pre-existing broker exposure.

Offline gold-rejection and repository-safety tests passed. At 2026-10-26 16:35 Asia/Tehran, the existing task was started without changing its definition. A subsequent fresh broker-reconciled heartbeat reported `HEALTHY`, five active workers S01–S05, thirteen blocked workers S06–S18, 475 closed DEMO trades, and no emergency stop. A read-only broker check observed a EURUSD position and no XAUUSD position. No manual/test order or REAL-account order was submitted.

The task's previous `0xC000013A` interruption may recur; the exact initiator remains unknown. The quote-freshness gate can transiently suspend new entries and must remain fail-closed. Gold remains unavailable for new live DEMO entries until a separately reviewed and authorized change.

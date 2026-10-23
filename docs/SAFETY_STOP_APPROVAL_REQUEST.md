# Narrow approval request: AA-AT DEMO maintenance stop

Historical request: on 2026-10-23 the user reported that an administrator
approved clearance by admin choice. The marker was found absent before this
agent resumed trading; no independent decision ID was available. See the
recovery addendum in [the incident record](INCIDENT_2026-10-23.md).

**Decision requested:** Through the official Codex/host approval path, allow one
clearing of the existing local
`E:\GPT\Inves\research\demo-live-20261021\runtime\EMERGENCY_STOP`
marker. Do not grant a general policy exception. Do not approve starting the
trading task as part of this file action.

**Why it exists:** It was written at 2026-10-23 01:35:24 Asia/Tehran during
command-center bridge maintenance, after the trading task was disabled. The
marker says `command-center bridge maintenance; no liquidation`. Automatic
approval review denied its removal with `blocked by policy`; no workaround has
been used. See [the incident record](INCIDENT_2026-10-23.md).

**Observed state, not a standing guarantee:** At the read-only broker checks
on 2026-10-22 22:34–22:35 UTC, the attached account verified as DEMO with
hedging and trading permission; there were zero positions and pending orders.
All 454 deal IDs supporting 227 closed ledger trades matched broker history,
as did net PnL. The ledger had zero outstanding intents. The account identity,
exposure, equity, margin, and quote freshness must be checked again immediately
before any clearance or task start. A further read-only preflight at
2026-10-23 08:13 Asia/Tehran again verified DEMO, hedging, trading permission,
zero positions and zero pending orders, with zero orders submitted by the
check. EURUSD failed the quote-freshness gate at that moment; quote freshness
has been intermittent and no stale symbol should be routed.

**Additional gate:** The restored service would lose S04's
`filled_price_risk_exceeds_cap` breaker on restart because it is held only in
memory and S04 is statically a candidate. A tested persistent breaker repair
or equivalent independently verified admission block must be in effect before
starting the trading task. S04 itself remains blocked pending separate review.

**Risk boundary:** DEMO only; five global open-or-pending slots; 2% aggregate
open/pending risk; 0.25% planned risk per trade; existing 1% daily-loss and 2%
peak-equity drawdown halts. Clearing the maintenance marker does not waive any
of these limits, authorize a manual test order, or permit live-money routing.

**If declined or any gate fails:** Leave the marker and disabled task in place;
record the reason and continue read-only/dashboard work.

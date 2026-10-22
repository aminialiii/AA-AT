# Next actions

1. Review the automation-branch pull request. The four-hour task, no-change behavior, and first scheduled changed synchronization are verified; the PR remains unmerged and undeployed.
2. Monitor the newly deployed five-slot, 2% aggregate DEMO policy across subsequent real signals. Confirm the 1% daily and 2% peak-equity halts, one-position-per-strategy rule, broker ownership, and per-order margin gate remain effective. Record real closed trades only after broker deal and position verification; do not force signals.
   Investigate repeated quote/clock freshness suspensions with broker timestamps and terminal health; preserve the current fail-closed routing behavior.
3. Investigate blocked S06–S18 individually. Implement adapters only where original rules are sufficiently specified; freeze each new executable version before forward testing.
   Examine a supported, credential-safe operating model if pre-login recovery after reboot is required; current tasks resume at user logon.
4. Update the dashboard and Graphify from verified operational state without publishing account numbers or trade-level evidence to Git.
5. At 100 genuine closed trades per strategy, inspect the immutable performance snapshot and continue valid DEMO execution. Repeat at 200, 500, 1,000, and every subsequent 500 trades. Do not interpret any milestone as proof of an edge.

Continuation command for a later Codex session: `Resume AA AT from E:\GPT\Inves\AA-AT\CHECKPOINT.json; verify current broker state and service health before making changes.`

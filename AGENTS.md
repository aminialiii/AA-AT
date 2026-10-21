# AA AT working instructions

Read `PROJECT_STATE.md`, `NEXT_ACTIONS.md`, and `CHECKPOINT.json` before changing the campaign. Preserve research baselines and the original workspace. Treat broker records as the only evidence of DEMO executions; documentation and static graphs do not prove live operation.

Never commit credentials, account identifiers, account-bound campaign config, order/deal records, runtime logs, or large market datasets. Use `tools/secret_scan.py` before commits. Keep `.env` local and review deployment separately. Do not run backtests or historical replay for the active forward campaign. Do not submit orders to a REAL account. Do not edit frozen strategy logic mid-campaign; use a new candidate/version after review.

Offline tests may parse code and configuration without importing the active service or calling broker APIs. Verify service health and reconcile broker state before changing or restarting execution components. Record meaningful milestones in the checkpoint files.

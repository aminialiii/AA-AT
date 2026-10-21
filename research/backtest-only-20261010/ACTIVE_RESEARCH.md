# Active offline research

Direct user demo suspension remains active. This directory grants no trading authorization.

Run the heartbeat entry point with the existing Python 3.14 runtime:

```powershell
& 'C:/Users/SOC-Peyman/AppData/Local/Python/pythoncore-3.14-64/python.exe' -B 'E:/GPT/Inves/research/backtest-only-20261010/cycle.py'
```

`active_program.json` points to the registered program. The entry point validates the prior completion receipt, frozen helper and input hashes, then runs one stage under exclusive locks. It does not call the broker.

## Completed program 01

The original `plan.json`, `request.json`, `state.json`, 35 stage artifacts and reports remain immutable. Its exact previous helper is preserved as `cycle_program01_immutable.py`. `program01_completed_receipt.json` records hashes of all completed results and trade archives. Do not replay these stages or modify their state.

## Active program 02

Directory: `extension-oct8-9-20261011`.

Registered interval: 2026-10-08 00:00 UTC inclusive through 2026-10-09 20:00 UTC exclusive. All seven original model choices and five hypothetical cost scenarios are fixed before replay. There is no new model search or strategy promotion.

The first stage, `BASELINE_XAUUSD`, completed once at 2026-10-11 13:44:45 UTC. The next stage is recorded in the active program's `state.json`; inspect that state instead of the completed parent state. Recover existing completed artifacts by hash without replay.

The interval contains only two entry dates and was partly exposed through earlier demo observations. It is a retrospective diagnostic, with hypothetical costs and an unverified tick path. Cost scenarios on shared data are not independent samples. Earlier end-censored trades stay separate; this program starts simulated flat and makes no carry-over claim.

Keep the 15-minute research heartbeat active. At program completion, register native tick validation or a genuinely new historical block before querying its outcomes. Never run the old overnight `cycle.js` or `release.py`, or resume demo from any research outcome.

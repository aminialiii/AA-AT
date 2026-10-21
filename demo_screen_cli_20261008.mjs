import { readFileSync, writeFileSync } from 'node:fs';
import { evaluateEventSetup } from './demo_event_setup_20261008.mjs';

const inputURL = new URL('./Demo_Screen_Input_20261008.json', import.meta.url);
const anchorURL = new URL('./Demo_Event_Anchor_20261008.json', import.meta.url);
const outputURL = new URL('./Demo_Screen_Output_20261008.json', import.meta.url);
const inputs = JSON.parse(readFileSync(inputURL, 'utf8'));
const eventAnchor = JSON.parse(readFileSync(anchorURL, 'utf8'));
const evaluatedAtUTC = new Date().toISOString();
const results = inputs.map(x => evaluateEventSetup({
  ...x,
  rulesVersion: 'US_FOMC_RANGE_RETEST_DYNAMIC_RISK_1',
  eventAnchor,
  nowUTC: evaluatedAtUTC
}));
writeFileSync(outputURL, JSON.stringify(results, null, 2));
console.log(JSON.stringify(results.map(r => ({
  symbol: r.state.symbol,
  status: r.status,
  reasons: r.reasons,
  active: r.state.active,
  proposal: r.proposal,
  context: r.context
}))));

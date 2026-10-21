import assert from 'node:assert/strict';
import {evaluateEventSetup,DYNAMIC_RULES} from '../../research_outputs/frozen/event_evaluator.mjs';
import {evaluateResearchEvent} from './event_adapter.mjs';
const anchor={releaseUTC:'2026-10-21T18:00:00Z',windowStartUTC:'2026-10-21T18:15:00Z',windowEndUTC:'2026-10-21T20:15:00Z',entryCutoffUTC:'2026-10-21T20:29:00Z',blocksUTC:[]};
const state={strategyVersion:DYNAMIC_RULES.version,symbol:'EURUSD',range:{high:1.2,low:1.1},active:null};
const bars=[0,5,10].map(n=>({timeUTC:`2026-10-21T18:${String(n).padStart(2,'0')}:00Z`,open:100,high:101,low:99,close:100}));
const input={rulesVersion:DYNAMIC_RULES.version,eventAnchor:anchor,state,nowUTC:'2026-10-21T18:20:00Z',dataAsOfUTC:'2026-10-21T18:20:00Z',actualServerOffsetMinutes:180,symbol:{name:'EURUSD'},M5:bars,M1:[],H1:[],quote:{}};
const original=evaluateEventSetup(input),fixed=evaluateResearchEvent(input);
assert.equal(original.state.range.high,1.2); // Reproduces unchanged-version anchor defect.
assert.equal(fixed.state.range.high,101);
assert.equal(fixed.state.range.low,99);
assert.equal(state.range.high,1.2); // Caller state preserved.
const repeat=evaluateResearchEvent({...input,state:fixed.state});
assert.deepEqual(repeat.state.range,fixed.state.range);
const unknown=evaluateResearchEvent({...input,M5:[]});
assert.equal(unknown.status,'unknown');assert.equal(unknown.state.range,null);
console.log(JSON.stringify({tests:6,status:'PASS',originalDefectReproduced:true,researchWrapperFixed:true,orders:0}));

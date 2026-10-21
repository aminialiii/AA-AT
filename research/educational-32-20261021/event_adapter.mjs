// Research-only state boundary wrapper. No files, host tools or order APIs.
import {evaluateEventSetup,DYNAMIC_RULES} from '../../research_outputs/frozen/event_evaluator.mjs';
export function evaluateResearchEvent(input){
 const state=structuredClone(input.state??{});
 const anchor=input.eventAnchor;
 if(input.rulesVersion===DYNAMIC_RULES.version&&anchor){
  const key=JSON.stringify([anchor.releaseUTC,anchor.windowStartUTC,anchor.windowEndUTC,anchor.entryCutoffUTC,anchor.blocksUTC]);
  if(state.eventAnchorKey!==key){
   state.range=null;state.active=null;state.lastProcessedM5OpenUTC=null;
   state.lastNewsResetStartUTC=null;state.requiredFreshBreakoutAfterUTC=null;
   state.invalidatedBreakouts=[];state.filledKeys=[];state.rejectedKeys=[];
   state.eventAnchorKey=key;
  }
 }
 return evaluateEventSetup({...input,state});
}

import fs from 'node:fs';
import path from 'node:path';
const R='E:/GPT/Inves/',sp=R+'Trading_Manager_State.json',s=JSON.parse(fs.readFileSync(sp,'utf8'));
const read=p=>JSON.parse(fs.readFileSync(p,'utf8'));
const save=(kind,data)=>{const p=R+'trading-journal/'+kind+'_'+Date.now()+'_'+Math.random().toString(36).slice(2,7)+'.json';fs.writeFileSync(p,JSON.stringify(data,null,2),{flag:'wx'});return p};
const release=key=>{const p=path.resolve(R+'trading-journal/execution.lock');if(path.dirname(p)!==path.resolve(R+'trading-journal'))throw Error('lock_path');if(fs.existsSync(p)){if(read(p).dedupKey!==key)throw Error('lock_owner');fs.unlinkSync(p)}};
const mode=process.argv[2];
const parallel=s.version.startsWith('DEMO_7_SYMBOLS_RR2_');
let result;
if(mode==='pending'){
 const intent=read(process.argv[3]),v=read(process.argv[4]),orders=v.matchingPendingOrders||[];
 if(orders.length!==1||v.matchingPositions.length||v.historicalFills.length)throw Error('pending_ambiguous');
 const o=orders[0],pre=read(intent.preflightPath),expected=Date.parse(pre.pendingExpiryUTC);
 const brokerExpiry=intent.request.expiration_type==='specified';
 if(!Number.isFinite(expected)||!o.sl||!o.tp||Math.abs(o.sl-intent.request.sl)>1e-8||Math.abs(o.tp-intent.request.tp)>1e-8||Math.abs(o.price_open-intent.request.price)>1e-8||brokerExpiry&&(!Number.isFinite(Date.parse(o.expirationUTC))||Math.abs(Date.parse(o.expirationUTC)-expected)>2000))throw Error('pending_price_protection_expiry_mismatch');
 const owner={orderTicket:o.ticket,symbol:o.symbol,dedupKey:intent.dedupKey,intentPath:process.argv[3],protocolPath:intent.protocolPath,preflightPath:intent.preflightPath,verificationPath:process.argv[4],expirationUTC:pre.pendingExpiryUTC,brokerExpirationUTC:o.expirationUTC,expiryPolicy:brokerExpiry?'BROKER':'ACTIVE_MANAGER_CANCEL_UNFILLED_ONLY',nativeMarginUSD:pre.marginUSD};
 if((s.owned_orders||[]).some(x=>x.dedupKey===owner.dedupKey))throw Error('duplicate_pending');
 s.owned_orders=[...(s.owned_orders||[]),owner];s.pending_intent=null;s.unknown_execution_outcome=false;s.stage='PENDING_VERIFIED';
 const p=save('rr2_pending_verified',{owner,order:o});release(owner.dedupKey);
 for(const i of s.intents)if(i.dedupKey===owner.dedupKey)Object.assign(i,{status:'PENDING_VERIFIED',orderTicket:o.ticket,verificationPath:process.argv[4]});
 result={status:s.stage,owner,path:p};
}else if(mode==='cancel_intent'){
 const intent=read(process.argv[3]),o=(s.owned_orders||[]).find(x=>x.dedupKey===intent.dedupKey);
 if(!o||o.cancelRequested)throw Error('cancel_unknown_or_already_requested_no_retry');
 const request={order_ticket:o.orderTicket,symbol:o.symbol};const p=save('rr2_unfilled_cancel_intent',{registeredUTC:new Date().toISOString(),dedupKey:'CANCEL_'+o.dedupKey,request,reason:'pending_validity_elapsed_unfilled_not_a_position_close'});
 Object.assign(o,{cancelRequested:true,cancelIntentPath:p});result={request,path:p};
}else if(mode==='cancel_ambiguous'){
 s.unknown_execution_outcome=true;s.unknown_cancel_key=process.argv[3];s.stage='RECONCILE_AMBIGUOUS_CANCEL';result={status:s.stage};
}else if(mode==='pending_done'){
 const intent=read(process.argv[3]),v=read(process.argv[4]),o=(s.owned_orders||[]).find(x=>x.dedupKey===intent.dedupKey),hist=v.matchingHistoryOrders;
 if(!o||v.matchingPositions.length||v.historicalFills.length||v.matchingPendingOrders.length||!hist?.length||hist.some(x=>![2,5,6].includes(x.state)))throw Error('pending_terminal_outcome_unknown');
 s.owned_orders=s.owned_orders.filter(x=>x.dedupKey!==o.dedupKey);const p=save('rr2_pending_terminal',{owner:o,history:hist,verificationPath:process.argv[4],countsAsTrade:false});
 if(s.unknown_cancel_key===o.dedupKey&&!s.pending_intent){s.unknown_execution_outcome=false;s.unknown_cancel_key=null}
 for(const i of s.intents)if(i.dedupKey===o.dedupKey)Object.assign(i,{status:'PENDING_TERMINAL_NO_FILL',terminalPath:p});
 s.stage='PREPARE';result={status:'PENDING_TERMINAL_NO_FILL',symbol:o.symbol,path:p};
}else if(mode==='fill'){
 const intent=read(process.argv[3]),verification=read(process.argv[4]),fills=[...verification.matchingPositions,...verification.historicalFills];
 if(fills.length!==1)throw Error('fill_ambiguous');
 const p=fills[0];if(s.owned_positions.some(x=>x.identifier===p.identifier))throw Error('duplicate_fill');const owner={ticket:p.ticket,identifier:p.identifier,symbol:p.symbol,side:p.type===0?'buy':'sell',volume:p.volume,entry:p.price_open,initialSL:p.sl,initialTP:p.tp,initialRiskUSD:p.initialRiskUSD,initialRewardUSD:p.initialRewardUSD,nativeActualRR:p.nativeActualRR,protectionValidAtFill:p.protectionValidAtFill,dedupKey:intent.dedupKey,protocolPath:intent.protocolPath,preflightPath:intent.preflightPath,verificationPath:process.argv[4],intentPath:process.argv[3],ordinal:intent.ordinal,row:intent.row,version:intent.row.version,kind:parallel?'ACTUAL_DEMO_SEVEN_SYMBOLS_RR2':'ACTUAL_DEMO_100_EXPLORATION'};
 const fillPath=save('hundred_fill',{owner,position:p});owner.fillPath=fillPath;
 s.owned_positions=parallel?[...s.owned_positions,owner]:[owner];s.owned_orders=(s.owned_orders||[]).filter(x=>x.dedupKey!==owner.dedupKey);if(s.pending_intent?.dedupKey===owner.dedupKey)s.pending_intent=null;if(!s.pending_intent&&(!s.unknown_cancel_key||s.unknown_cancel_key===owner.dedupKey)){s.unknown_execution_outcome=false;s.unknown_cancel_key=null}s.stage='MANAGE';s.filled_entries++;s.last_actual_fill_path=fillPath;
 if(parallel){const lp=R+'trading-journal/execution.lock';if(fs.existsSync(lp)&&read(lp).dedupKey===owner.dedupKey)release(owner.dedupKey)}
 for(const i of s.intents)if(i.dedupKey===owner.dedupKey)Object.assign(i,{status:'FILL_VERIFIED',ticket:p.ticket,fillPath});
 result={owner};
}else if(mode==='reject'){
 const intent=read(process.argv[3]),reason=process.argv[4];save('hundred_not_filled',{intent,reason});s.pending_intent=null;s.stage='HUNDRED_PREPARE';
 for(const i of s.intents)if(i.dedupKey===intent.dedupKey)i.status=reason;
 release(intent.dedupKey);result={status:reason};
}else if(mode==='ambiguous'){
 s.unknown_execution_outcome=true;s.stage='RECONCILE_AMBIGUOUS';result={status:s.stage};
}else if(mode==='close'){
 const reconciliation=read(process.argv[3]),owner=s.owned_positions.find(p=>p.ticket===reconciliation.ticket);
 if(!owner)throw Error('owner_missing');
 if(s.hundred.results.some(x=>x.identifier===reconciliation.identifier))throw Error('duplicate_close');
 const row={...owner.row,side:owner.side,volume:owner.volume,ticket:owner.ticket,identifier:reconciliation.identifier,netUSD:reconciliation.netUSD,grossUSD:reconciliation.grossUSD,commissionUSD:reconciliation.commissionUSD,swapUSD:reconciliation.swapUSD,feesUSD:reconciliation.feesUSD,initialRiskUSD:reconciliation.initialRiskUSD,nativeActualRR:reconciliation.nativeActualRR,exitReason:reconciliation.exitReason,netR:reconciliation.netR,holdingSeconds:reconciliation.holdingSeconds,MAEPriceObserved:reconciliation.MAEPriceObserved,MFEPriceObserved:reconciliation.MFEPriceObserved,recordedUTC:reconciliation.recordedUTC,preflightPath:owner.preflightPath,reconciliationPath:process.argv[3]};
 s.hundred.results.push(row);s.hundred.closed++;s.hundred.netUSD=Number((s.hundred.netUSD+row.netUSD).toFixed(8));s.hundred.wins+=row.netUSD>0?1:0;s.hundred.losses+=row.netUSD<0?1:0;
 s.owned_positions=s.owned_positions.filter(p=>p.ticket!==owner.ticket);s.stage='HUNDRED_PREPARE';s.last_actual_close_path=process.argv[3];s.last_reconciliation_path=process.argv[3];s.observed_peak_equity=Math.max(s.observed_peak_equity,reconciliation.currentBalanceUSD);
 for(const i of s.intents)if(i.dedupKey===owner.dedupKey)Object.assign(i,{status:'CLOSED_RECONCILED',reconciliationPath:process.argv[3]});
 save('hundred_closed_checkpoint',{row,completed:s.hundred.closed,netUSD:s.hundred.netUSD,balanceUSD:reconciliation.currentBalanceUSD});if(!parallel)release(owner.dedupKey);
 result={status:'CLOSED_RECONCILED',completed:s.hundred.closed,target:s.hundred.target,netUSD:s.hundred.netUSD,balanceUSD:reconciliation.currentBalanceUSD,last:row,deadlineUTC:s.hundred.deadlineUTC};
}else if(mode==='stop'){
 if(s.owned_positions.length||s.owned_orders?.length||s.pending_intent||s.unknown_execution_outcome)throw Error('exposure_not_reconciled');
 s.run_status='STOPPED';s.stage=s.hundred.closed>=s.hundred.target?'TARGET_COMPLETE':'EXPERIMENT_DEADLINE';s.hundred.finishedUTC=new Date().toISOString();
 const cp=R+'Trading_Manager_Config.json',c=read(cp);c.enabled=false;fs.writeFileSync(cp,JSON.stringify(c,null,2));result={status:s.stage,hundred:s.hundred};
}else throw Error('unknown_mode');
fs.writeFileSync(sp,JSON.stringify(s,null,2));console.log(JSON.stringify(result));

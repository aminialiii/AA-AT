(async()=>{
 const ROOT='E:/GPT/Inves';
 const parse=r=>{if(r?.isError)throw Error(r.content?.find(x=>x.type==='text')?.text??'MCP_error');return r.structuredContent??JSON.parse(r.content.find(x=>x.type==='text').text)};
 const command=async cmd=>{const r=await tools.exec_command({cmd,max_output_tokens:16000});if(r.exit_code!==0)throw Error(r.output);return r.output};
 const artifact=async(kind,data)=>{const id=Date.now()+'_'+Math.random().toString(36).slice(2,7),stage=ROOT+'/.skill-tools/'+kind+'_stage_'+id+'.json',path=ROOT+'/trading-journal/'+kind+'_'+id+'.json';await tools.apply_patch('*** Begin Patch\n*** Add File: '+stage+'\n+'+JSON.stringify(data)+'\n*** End Patch');await command("node 'E:/GPT/Inves/.skill-tools/immutable-json-write.mjs' '"+path+"' '"+stage+"'");return path};
 const checkpoint=async u=>{const path=await artifact('universe_checkpoint',u);await command("@'\nimport fs from 'node:fs';const p='E:/GPT/Inves/Trading_Manager_State.json',s=JSON.parse(fs.readFileSync(p,'utf8')),u=JSON.parse(fs.readFileSync('"+path+"','utf8'));Object.assign(s,u.set??{});if(u.consumed)s.consumed_signals=[...new Set([...s.consumed_signals,...u.consumed])];fs.writeFileSync(p,JSON.stringify(s,null,2));\n'@ | node --input-type=module -")};
 const native=async args=>{let r=await tools.exec_command({cmd:"& 'C:/Users/SOC-Peyman/AppData/Local/Python/pythoncore-3.14-64/python.exe' 'E:/GPT/Inves/.skill-tools/universe-native.py' "+args,sandbox_permissions:'require_escalated',justification:'Read-only native inventory and all-symbol screening on the user-authorized matching demo account. Python sends no orders and changes no account or settings.',yield_time_ms:10000,max_output_tokens:6000});let output=r.output;while(r.session_id){r=await tools.write_stdin({session_id:r.session_id,chars:'',yield_time_ms:10000,max_output_tokens:6000});output+=r.output}if(r.exit_code!==0)throw Error(output);return output.trim().split(/\r?\n/).filter(Boolean).map(x=>JSON.parse(x))};
 parse(await tools.mcp__terminal__get_workspace_info({}));store('micromap_candidate',null);store('micromap_candidate_path',null);store('micromap_management',null);
 const phase={startedUTC:new Date().toISOString()};
 const batch=await Promise.allSettled([tools.mcp__terminal__get_time_information({}),tools.mcp__terminal__get_trading_account_info({}),tools.mcp__terminal__get_trading_open_positions({include_orders:true}),tools.exec_command({cmd:"@'\nimport fs from 'node:fs';const r='E:/GPT/Inves/';let cache=null;try{cache=JSON.parse(fs.readFileSync(r+'.skill-tools/universe-news-cache.json','utf8'))}catch{}console.log(JSON.stringify({config:JSON.parse(fs.readFileSync(r+'Trading_Manager_Config.json','utf8')),state:JSON.parse(fs.readFileSync(r+'Trading_Manager_State.json','utf8')),cache}));\n'@ | node --input-type=module -",max_output_tokens:24000})]);
 if(batch.some(x=>x.status==='rejected'))throw Error('preflight_failed');
 const [time,acct,open]=batch.slice(0,3).map(x=>parse(x.value)),{config,state,cache}=JSON.parse(batch[3].value.output),a=acct.account;
 if(config.risk_policy?.type!=='user_waiver_demo_only'||config.universe_policy?.scope!=='all_broker_symbols')throw Error('unsupported_config');
 if(a.type!=='demo'||a.currency!=='USD'||a.login!==config.account_login||a.server!==config.account_server||a.read_only||!acct.terminal.server_connected||!acct.terminal.mcp_trade_allowed)throw Error('matching_writable_demo_required');
 if(!config.enabled||state.run_status!=='ACTIVE'){text({status:'STOPPED'});return}
 if(state.owned_positions?.length||state.pending_intent||state.unknown_execution_outcome){store('micromap_management',{account:a,open,state});text({status:'MANAGEMENT_REQUIRED'});return}
 const now=Date.parse(time.utc_time),offset=Math.round((Date.parse(time.trade_server_last_known_time+'Z')-now)/60000);
 if(offset!==config.broker_UTC_offset_minutes)throw Error('broker_clock_unknown');
 if(now>=Date.parse(config.session_end_utc)){text({status:'SESSION_ENDED'});return}
 const plan=(await native('plan'))[0];store('universe_plan',plan);
 if(plan.status!=='universe_ready'){text(plan);return}
 const additions=[];
 for(const name of plan.symbolsToAdd){const r=await tools.mcp__terminal__add_marketwatch_symbol({symbol:name,show:true});if(r.isError)throw Error('Market_Watch_add_failed:'+name);additions.push({symbol:name,result:r})}
 const confirmedWatch=parse(await tools.mcp__terminal__get_marketwatch_symbols({include_hidden:false,limit:1000}));
 if(plan.symbolsToAdd.some(name=>!confirmedWatch.symbols.some(s=>s.symbol===name&&s.selected)))throw Error('Market_Watch_visibility_not_confirmed');
 const selectionPath=await artifact('universe_marketwatch_selection',{recordedUTC:new Date().toISOString(),plan,additions});
 await checkpoint({set:{universe_cursor:plan.nextCursor,universe_initialized:true,last_universe_plan_path:plan.path,last_marketwatch_selection_path:selectionPath}});
 phase.marketWatchCompletedUTC=new Date().toISOString();
 const freshTime=parse(await tools.mcp__terminal__get_time_information({})),newsNow=Date.parse(freshTime.utc_time),newsOffset=Math.round((Date.parse(freshTime.trade_server_last_known_time+'Z')-newsNow)/60000);
 if(newsOffset!==offset)throw Error('clock_changed');
 const from=newsNow-20*60000,to=newsNow+120*60000,server=x=>new Date(x+offset*60000).toISOString().slice(0,19),byCurrency={},metadataResults=[];
 const calendarPromise=tools.mcp__terminal__economic_calendar_list_values({datetime_from:server(from),datetime_to:server(to),limit:1000});
 const met=await Promise.allSettled(plan.relevantCurrencies.map(async c=>{
  const old=cache?.byCurrency?.[c];
  if(old?.ok&&Date.now()-Date.parse(old.metadataUTC)<15*60000)return {currency:c,cached:true,data:old};
  const raw=await tools.mcp__terminal__economic_calendar_list_events_by_currency({currency_code:c}),data=parse(raw);
  return {currency:c,cached:false,data,raw};
 }));
 for(let i=0;i<met.length;i++){
  const r=met[i],c=plan.relevantCurrencies[i];
  if(r.status==='rejected'){byCurrency[c]={ok:false,metadataUTC:new Date().toISOString(),events:[],error:String(r.reason)};continue}
  const v=r.value;
  if(v.cached){byCurrency[c]=v.data;continue}
  const evidencePath=await artifact('universe_calendar_metadata_'+c,{recordedUTC:new Date().toISOString(),currency:c,response:v.raw});
  byCurrency[c]={ok:v.data.ok===true,metadataUTC:new Date().toISOString(),eventSeriesCount:v.data.events?.length??0,events:(v.data.events??[]).filter(e=>e.importance==='High importance').map(e=>({id:e.id,importance:e.importance})),evidencePath};
  metadataResults.push({currency:c,ok:byCurrency[c].ok,highImpactSeries:byCurrency[c].events.length});
 }
 const calendar=parse(await calendarPromise);
 const news={calendar,byCurrency,collectedUTC:new Date().toISOString(),offsetMinutes:offset,coverageFromUTC:new Date(from).toISOString(),coverageToUTC:new Date(to).toISOString(),scope:'symbol_specific_currencies'};
 const newsPath=await artifact('universe_news',news);
 await command("Copy-Item -LiteralPath '"+newsPath+"' -Destination 'E:/GPT/Inves/.skill-tools/universe-news-cache.json' -Force");
 phase.calendarCompletedUTC=new Date().toISOString();
 const observations=await native('watch '+(load('micromap_watch_samples')??2)),last=observations.at(-1);
 phase.completedUTC=new Date().toISOString();
 for(const o of observations){if(o.candidate){store('micromap_candidate',o.candidate);store('micromap_candidate_path',o.candidatePath);store('micromap_snapshot_path',o.snapshotPath)}if(o.status==='MANAGEMENT_REQUIRED')store('micromap_management',o)}
 const consumed=[...new Set(observations.flatMap(o=>o.consumedSignals??[]))];
 const auditPath=await artifact('universe_cycle',{phase,version:config.version,riskPolicy:config.risk_policy_revision,financialCapsApplied:false,plan,selectionPath,newsPath,metadataResults,observations,ordersSubmitted:0});
 await checkpoint({set:{last_phase:phase,last_cycle_utc:phase.completedUTC,last_cycle_audit_path:auditPath,last_snapshot_path:last?.snapshotPath,stage:last?.status==='analysis_ready'?'EXECUTION_GATE':'WAIT',observed_peak_equity:Math.max(state.observed_peak_equity??0,a.equity),next_action:'All broker symbols are authorized. Use fresh normalized candidates, exact native profit/margin and continuous owned-position management. No active recurring scheduler is available.'},consumed});
 text({status:last?.status??'no_observation',brokerCatalogCount:plan.brokerSymbolCount,screenedSymbols:last?.screenedSymbols,addedSymbols:plan.symbolsToAdd,last,cyclePath:auditPath,phase,ordersSubmitted:0});
})();

(async()=>{
 const ROOT='E:/GPT/Inves',parse=r=>{if(r?.isError)throw Error(r.content?.find(x=>x.type==='text')?.text??'tool_error');return r.structuredContent??JSON.parse(r.content.find(x=>x.type==='text').text)};
 parse(await tools.mcp__terminal__get_workspace_info({}));store('micromap_candidate',null);store('micromap_management',null);
 const phase={startedUTC:new Date().toISOString()};
 const batch=await Promise.allSettled([
  tools.mcp__terminal__get_time_information({}),tools.mcp__terminal__get_trading_account_info({}),tools.mcp__terminal__get_trading_open_positions({include_orders:true}),
  tools.exec_command({cmd:"@'\nimport fs from 'node:fs';const r='E:/GPT/Inves/';let cache=null;try{const c=JSON.parse(fs.readFileSync(r+'.skill-tools/micromap-news-cache.json','utf8'));cache={metadataUTC:c.metadataUTC,events:{ok:c.events.ok,events:c.events.events.map(e=>({id:e.id,importance:e.importance}))}}}catch{}console.log(JSON.stringify({config:JSON.parse(fs.readFileSync(r+'Trading_Manager_Config.json','utf8')),state:JSON.parse(fs.readFileSync(r+'Trading_Manager_State.json','utf8')),cache}));\n'@ | node --input-type=module -",max_output_tokens:12000})
 ]);
 if(batch.some(x=>x.status==='rejected'))throw Error('preflight_failed');
 const [time,acct,open]=batch.slice(0,3).map(x=>parse(x.value)),{config,state,cache}=JSON.parse(batch[3].value.output),a=acct.account;
 if(!config.enabled||state.run_status!=='ACTIVE'){text({status:'STOPPED'});return}
 if(config.risk_policy?.type!=='user_waiver_demo_only'||!config.version.startsWith('POURSAMADI_MICROMAP_'))throw Error('unsupported_config');
 if(a.type!=='demo'||a.currency!=='USD'||a.login!==config.account_login||a.server!==config.account_server||a.read_only||!acct.terminal.server_connected||!acct.terminal.mcp_trade_allowed)throw Error('demo_account_gate');
 if(state.owned_positions?.length||state.pending_intent||state.unknown_execution_outcome){store('micromap_management',{account:a,open,state});text({status:'MANAGEMENT_REQUIRED',open});return}
 const now=Date.parse(time.utc_time),offset=Math.round((Date.parse(time.trade_server_last_known_time+'Z')-now)/60000);
 if(offset!==config.broker_UTC_offset_minutes)throw Error('broker_clock_unknown');
 if(now>=Date.parse(config.session_end_utc)){text({status:'SESSION_ENDED'});return}
 const iso=x=>new Date(x+offset*60000).toISOString().slice(0,19),from=now-20*60000,to=now+120*60000;
 const cacheValid=cache&&Date.now()-Date.parse(cache.metadataUTC)<15*60000;
 const nr=await Promise.allSettled([tools.mcp__terminal__economic_calendar_list_values({datetime_from:iso(from),datetime_to:iso(to),limit:1000}),cacheValid?Promise.resolve(cache.events):tools.mcp__terminal__economic_calendar_list_events_by_currency({currency_code:'USD'})]);
 if(nr.some(x=>x.status==='rejected'))throw Error('calendar_unknown');
 const calendar=parse(nr[0].value),events=cacheValid?nr[1].value:parse(nr[1].value);
 if(!calendar.ok||calendar.truncated||!events.ok||!Array.isArray(events.events))throw Error('calendar_unknown');
 const news={calendar,events,collectedUTC:new Date().toISOString(),metadataUTC:cacheValid?cache.metadataUTC:new Date().toISOString(),offsetMinutes:offset,coverageFromUTC:new Date(from).toISOString(),coverageToUTC:new Date(to).toISOString(),symbol:'XAUUSD'};
 const id=Date.now(),stage=ROOT+'/.skill-tools/micromap-news-stage_'+id+'.json',newsPath=ROOT+'/trading-journal/micromap_news_'+id+'.json';
 await tools.apply_patch('*** Begin Patch\n*** Add File: '+stage+'\n+'+JSON.stringify(news)+'\n*** End Patch');
 const write=await tools.exec_command({cmd:"node 'E:/GPT/Inves/.skill-tools/immutable-json-write.mjs' '"+newsPath+"' '"+stage+"'",max_output_tokens:1000});if(write.exit_code!==0)throw Error('news_journal_failed');
 const cacheWrite=await tools.exec_command({cmd:"Copy-Item -LiteralPath '"+stage+"' -Destination 'E:/GPT/Inves/.skill-tools/micromap-news-cache.json' -Force",max_output_tokens:1000});if(cacheWrite.exit_code!==0)throw Error('news_cache_failed');
 store('micromap_news_path',newsPath);phase.calendarCompletedUTC=new Date().toISOString();
 const samples=load('micromap_watch_samples')??4;
 let run=await tools.exec_command({cmd:"& 'C:/Users/SOC-Peyman/AppData/Local/Python/pythoncore-3.14-64/python.exe' 'E:/GPT/Inves/.skill-tools/micromap-native.py' watch "+samples,sandbox_permissions:'require_escalated',justification:'Read-only native gold observation for the user-authorized demo experiment; Python sends no orders and changes no account or terminal settings.',yield_time_ms:10000,max_output_tokens:3000});
 let output=run.output;
 while(run.session_id){run=await tools.write_stdin({session_id:run.session_id,chars:'',yield_time_ms:10000,max_output_tokens:3000});output+=run.output;}
 if(run.exit_code!==0)throw Error('native_screen_failed:'+output);
 const observations=output.trim().split(/\r?\n/).map(x=>{try{return JSON.parse(x)}catch{return null}}).filter(Boolean),last=observations.at(-1);
 phase.completedUTC=new Date().toISOString();
 for(const o of observations){if(o.candidate){store('micromap_candidate',o.candidate);store('micromap_candidate_path',o.candidatePath);store('micromap_snapshot_path',o.snapshotPath)}if(o.status==='MANAGEMENT_REQUIRED')store('micromap_management',o)}
 const consumed=[...new Set(observations.flatMap(x=>x.consumedSignals??[]))];
 const audit={phase,version:config.version,riskPolicy:config.risk_policy_revision,oldPercentageCapsApplied:false,newsPath,observations,ordersSubmitted:0};
 const auditStage=ROOT+'/.skill-tools/micromap-cycle-stage_'+Date.now()+'.json',auditPath=ROOT+'/trading-journal/micromap_cycle_'+Date.now()+'.json';
 await tools.apply_patch('*** Begin Patch\n*** Add File: '+auditStage+'\n+'+JSON.stringify(audit)+'\n*** End Patch');
 const aw=await tools.exec_command({cmd:"node 'E:/GPT/Inves/.skill-tools/immutable-json-write.mjs' '"+auditPath+"' '"+auditStage+"'",max_output_tokens:1000});if(aw.exit_code!==0)throw Error('cycle_journal_failed');
 const update={phase,auditPath,last,consumed,peak:a.equity},updatePath=ROOT+'/.skill-tools/micromap-update_'+Date.now()+'.json';
 await tools.apply_patch('*** Begin Patch\n*** Add File: '+updatePath+'\n+'+JSON.stringify(update)+'\n*** End Patch');
 const cp=await tools.exec_command({cmd:"@'\nimport fs from 'node:fs';const p='E:/GPT/Inves/Trading_Manager_State.json',s=JSON.parse(fs.readFileSync(p,'utf8')),u=JSON.parse(fs.readFileSync('"+updatePath+"','utf8'));s.last_phase=u.phase;s.last_cycle_utc=u.phase.completedUTC;s.last_cycle_audit_path=u.auditPath;s.last_snapshot_path=u.last?.snapshotPath;s.stage=u.last?.status==='analysis_ready'?'EXECUTION_GATE':'WAIT';s.observed_peak_equity=Math.max(s.observed_peak_equity,u.peak);s.consumed_signals=[...new Set([...s.consumed_signals,...u.consumed])];s.next_action='Use current demo waiver; execute only a fresh numerical MicroMAP candidate after new preflight/native margin/unique intent. Old percentage/DD/loss/fill ceilings are disabled.';fs.writeFileSync(p,JSON.stringify(s,null,2));\n'@ | node --input-type=module -",max_output_tokens:1000});if(cp.exit_code!==0)throw Error('state_checkpoint_failed');
 text({status:last?.status??'no_observation',last,observations:observations.length,cyclePath:auditPath,phase,riskPolicy:config.risk_policy_revision,ordersSubmitted:0});
})();

(async()=>{
 const ROOT='E:\\GPT\\Inves',SKILL='C:\\Users\\SOC-Peyman\\.codex\\skills\\mt5-trading-manager\\scripts';
 const parse=r=>{if(r?.isError)throw Error(r.content?.find(x=>x.type==='text')?.text??'tool_error');return r.structuredContent??JSON.parse(r.content.filter(x=>x.type==='text')[0].text)};
 parse(await tools.mcp__terminal__get_workspace_info({}));
 const phase={startedUTC:new Date().toISOString()};
 const settled=await Promise.allSettled([tools.mcp__terminal__get_time_information({}),tools.mcp__terminal__get_trading_account_info({}),tools.mcp__terminal__get_trading_open_positions({include_orders:true}),tools.exec_command({cmd:"Get-Content -LiteralPath 'E:\\GPT\\Inves\\Trading_Manager_State.json' -Raw",max_output_tokens:10000}),tools.exec_command({cmd:"Get-Content -LiteralPath 'E:\\GPT\\Inves\\Trading_Manager_Config.json' -Raw",max_output_tokens:10000})]);
 if(settled.some(x=>x.status==='rejected'))throw Error('preflight_call_failed');
 if(settled[3].value.exit_code!==0||settled[4].value.exit_code!==0)throw Error('runtime_file_read_failed');
 const [time,acct,open]=settled.slice(0,3).map(x=>parse(x.value)),state=JSON.parse(settled[3].value.output),config=JSON.parse(settled[4].value.output),account=acct.account;
 if(state.run_status!=='ACTIVE'||!config.enabled){text({status:'STOPPED'});return;}
 if(account.type!=='demo'||account.currency!=='USD'||account.login!==config.account_login||account.server!==config.account_server||account.read_only||!acct.terminal.server_connected||!acct.terminal.mcp_trade_allowed)throw Error('account_gate');
 if(open.positions.length||open.orders.length||state.owned_positions?.length||state.pending_intent||state.unknown_execution_outcome){store('trading_manager_management',{account,open,state});text({status:'MANAGEMENT_REQUIRED',positions:open.positions,orders:open.orders});return;}
 const symbols=config.symbols;
 if(!Array.isArray(symbols)||!symbols.length||new Set(symbols).size!==symbols.length)throw Error('configured_symbols_invalid');
 const now=Date.parse(time.utc_time),server=Date.parse(time.trade_server_last_known_time+'Z'),offsetMinutes=Math.round((server-now)/60000);
 if(!Number.isFinite(offsetMinutes)||Math.abs(offsetMinutes)>840)throw Error('clock_offset_unknown');
 const iso=t=>new Date(t+offsetMinutes*60000).toISOString().slice(0,19);
 phase.preflightCompletedUTC=new Date().toISOString();
 const periodMs={M5:300000,M1:60000};
 const fetchClosed=async(symbol,period)=>{
  const requestedUTC=new Date().toISOString(),cutoff=Date.parse(requestedUTC);
  const response=parse(await tools.mcp__terminal__get_chart_history({symbol,period,datetime_from:iso(cutoff-(period==='M1'?2:12)*3600000),datetime_to:iso(cutoff+60000),limit:500}));
  const closed=response.history.filter(bar=>{const stamp=Date.parse((bar.timeUTC??bar.time)+(String(bar.timeUTC??bar.time).endsWith('Z')?'':'Z'))-(bar.timeUTC?0:offsetMinutes*60000);return Number.isFinite(stamp)&&stamp+periodMs[period]<=cutoff;});
  return {history:closed,requestedUTC,completedUTC:new Date().toISOString(),excludedOpenBars:response.history.length-closed.length};
 };
 const calendar=parse(await tools.mcp__terminal__economic_calendar_list_values({datetime_from:iso(now-20*60000),datetime_to:iso(now+90*60000),limit:100}));
 let metadata;
 if(state.last_snapshot_path){
  const cacheRead=await tools.exec_command({cmd:"@'\nimport fs from 'node:fs';\nimport path from 'node:path';\nconst state=JSON.parse(fs.readFileSync('E:/GPT/Inves/Trading_Manager_State.json','utf8'));\nconst target=path.resolve(state.last_snapshot_path);\nconst rel=path.relative(path.resolve('E:/GPT/Inves/trading-journal'),target);\nif(rel.startsWith('..')||path.isAbsolute(rel))throw Error('metadata_path_rejected');\nconst x=JSON.parse(fs.readFileSync(target,'utf8'));\nconsole.log(JSON.stringify({utc:x.calendarMetadataUTC??x.timeProvenance?.accountAndPositionsUTC??x.utc,countries:x.countries,details:x.calendarDetails}));\n'@ | node --input-type=module -",max_output_tokens:10000});
  if(cacheRead.exit_code===0){try{const cached=JSON.parse(cacheRead.output);if(now-Date.parse(cached.utc)>=0&&now-Date.parse(cached.utc)<=15*60000&&Array.isArray(cached.countries)&&Array.isArray(cached.details))metadata=cached;}catch{}}
 }
 const countries=metadata?{countries:metadata.countries}:parse(await tools.mcp__terminal__economic_calendar_list_countries({}));
 const ids=[...new Set(calendar.values.map(x=>x.event_id))];
 const details=await Promise.allSettled(ids.map(async event_id=>{
  const cached=metadata?.details.find(x=>x.event_id===event_id&&x.data?.event&&!x.error);
  return cached??{event_id,data:parse(await tools.mcp__terminal__economic_calendar_get_event_by_id({event_id}))};
 }));
 phase.calendarCompletedUTC=new Date().toISOString();
 const m5=await Promise.allSettled(symbols.map(symbol=>fetchClosed(symbol,'M5')));
 if(m5.some(x=>x.status==='rejected'))throw Error('M5_history_failed');
 phase.M5CompletedUTC=new Date().toISOString();
 const m1=await Promise.allSettled(symbols.map(symbol=>fetchClosed(symbol,'M1')));
 if(m1.some(x=>x.status==='rejected'))throw Error('M1_history_failed');
 phase.historyCompletedUTC=new Date().toISOString();
 const watch=parse(await tools.mcp__terminal__get_marketwatch_symbols({include_hidden:false,limit:1000}));
 phase.quotesCompletedUTC=new Date().toISOString();
 const endTime=parse(await tools.mcp__terminal__get_time_information({})),utc=endTime.utc_time;
 const endOffset=Math.round((Date.parse(endTime.trade_server_last_known_time+'Z')-Date.parse(utc))/60000);
 if(endOffset!==offsetMinutes)throw Error('clock_offset_changed');
 const marketRecords=symbols.map((symbol,i)=>{
  const found=watch.symbols.filter(s=>s.symbol===symbol);
  if(found.length!==1||!found[0].update_time||!(found[0].ask>0)||!(found[0].bid>0))throw Error(symbol+'_quote_missing');
  return {symbol:found[0],M5:m5[i].value.history,M1:m1[i].value.history,historyAsOf:{M5:m5[i].value.requestedUTC,M1:m1[i].value.requestedUTC},excludedOpenBars:{M5:m5[i].value.excludedOpenBars,M1:m1[i].value.excludedOpenBars}};
 });
 const snapshot={utc,offsetMinutes,account,terminal:acct.terminal,positions:open.positions,orders:open.orders,symbols:marketRecords,calendar,countries:countries.countries,calendarDetails:details.map(x=>x.status==='fulfilled'?x.value:{error:'event_details_unknown'}),calendarMetadataUTC:metadata?.utc??time.utc_time,calendarMetadataCached:!!metadata,phase,collectorVersion:'CLOSED_BARS_FINAL_QUOTE_EXCLUSIVE_JOURNAL_2',timeProvenance:{accountAndPositionsUTC:time.utc_time,historiesRequestedUTC:time.utc_time,quoteRequestCompletedUTC:phase.quotesCompletedUTC}};
 const id=utc.replace(/[^0-9]/g,'')+'_'+Date.now();
 const input=ROOT+'\\trading-journal\\snapshot_'+id+'.json',output=ROOT+'\\trading-journal\\analysis_'+id+'.json';
 const staging=ROOT+'\\.skill-tools\\snapshot-stage_'+id+'.json';
 store('trading_manager_snapshot',snapshot);
 store('trading_manager_pending_snapshot',{input,output,staging});
 await tools.apply_patch('*** Begin Patch\n*** Add File: '+staging+'\n+'+JSON.stringify(snapshot)+'\n*** End Patch');
 const write=await tools.exec_command({cmd:"node 'E:\\GPT\\Inves\\.skill-tools\\immutable-json-write.mjs' '"+input+"' '"+staging+"'",max_output_tokens:1000});
 if(write.exit_code!==0){text({stage:'snapshot_write',result:write});throw Error('exclusive_snapshot_write_failed');}
 const cli=await tools.exec_command({cmd:"node '"+SKILL+"\\manager-cli.mjs' '"+input+"' '"+output+"'",max_output_tokens:10000});
 if(cli.exit_code!==0)throw Error('analysis_cli_failed');
 const analysis=JSON.parse(cli.output);phase.completedUTC=new Date().toISOString();
 const latestRead=await tools.exec_command({cmd:"Get-Content -LiteralPath 'E:\\GPT\\Inves\\Trading_Manager_State.json' -Raw",max_output_tokens:10000});
 if(latestRead.exit_code!==0)throw Error('checkpoint_read_failed');
 const latestState=JSON.parse(latestRead.output);
 if(latestState.run_status!=='ACTIVE'){text({status:'STOPPED',input,output});return;}
 const nextState={...latestState,stage:'WAIT',last_cycle_utc:utc,last_analysis_path:output,last_snapshot_path:input,last_phase:phase,observed_peak_equity:Math.max(latestState.observed_peak_equity,account.equity),next_action:'confirm fresh candidate; require new execution preflight; never force an entry'};
 const stateText=latestRead.output.replace(/\r\n/g,'\n').replace(/\n$/,'').split('\n');
 await tools.apply_patch('*** Begin Patch\n*** Update File: '+ROOT+'\\Trading_Manager_State.json\n@@\n'+stateText.map(x=>'-'+x).join('\n')+'\n+'+JSON.stringify(nextState)+'\n*** End Patch');
 store('trading_manager_snapshot',snapshot);store('trading_manager_analysis',analysis);
 text({status:'SCREENED',input,output,phase,analysis,collectorVersion:snapshot.collectorVersion,quoteAgesSeconds:marketRecords.map(x=>({symbol:x.symbol.symbol,age:(Date.parse(utc)-(Date.parse(x.symbol.update_time+'Z')-offsetMinutes*60000))/1000})),calendarDetails:snapshot.calendarDetails,calendar:calendar.values});
})();

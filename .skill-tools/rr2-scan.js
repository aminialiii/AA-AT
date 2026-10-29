(async()=>{
 const ROOT='E:/GPT/Inves',parse=r=>{if(r?.isError)throw Error('MCP_error');return r.structuredContent??JSON.parse(r.content.find(x=>x.type==='text').text)};
 parse(await tools.mcp__terminal__get_workspace_info({}));
 const command=async cmd=>{const r=await tools.exec_command({cmd,max_output_tokens:2500});if(r.exit_code!==0)throw Error(r.output);return r.output;};
 const native=async args=>{let r=await tools.exec_command({cmd:"& 'C:/Users/SOC-Peyman/AppData/Local/Python/pythoncore-3.14-64/python.exe' 'E:/GPT/Inves/.skill-tools/rr2-native.py' "+args,sandbox_permissions:'require_escalated',justification:'Read-only all-symbol demo analysis authorized by the user. No native order send, account change or intent creation.',max_output_tokens:3500});let out=r.output;while(r.session_id){r=await tools.write_stdin({session_id:r.session_id,chars:'',yield_time_ms:10000,max_output_tokens:3500});out+=r.output;}if(r.exit_code!==0)throw Error(out);return JSON.parse(out.trim().split(/\r?\n/).at(-1));};
 const state=JSON.parse(await command("$s=Get-Content -LiteralPath 'E:/GPT/Inves/Trading_Manager_State.json' -Raw | ConvertFrom-Json; [pscustomobject]@{owned_positions=@($s.owned_positions);pending_intent=$s.pending_intent;unknown_execution_outcome=$s.unknown_execution_outcome} | ConvertTo-Json -Depth 15 -Compress"));
 if(state.owned_positions.length||state.pending_intent||state.unknown_execution_outcome)return {status:'MANAGEMENT_OR_RECONCILIATION_REQUIRED',owned:state.owned_positions};
 const plan=await native('plan');if(plan.status==='deadline')return plan;
 for(const symbol of plan.symbolsToAdd){const r=await tools.mcp__terminal__add_marketwatch_symbol({symbol,show:true});if(r.isError)return {status:'MARKET_WATCH_ERROR',symbol,response:r};}
 const tm=parse(await tools.mcp__terminal__get_time_information({})),now=Date.parse(tm.utc_time),offset=Math.round((Date.parse(tm.trade_server_last_known_time+'Z')-now)/60000);if(offset!==180)throw Error('clock_unknown');
 const server=ms=>new Date(ms+offset*60000).toISOString().slice(0,19);
 const calendar=parse(await tools.mcp__terminal__economic_calendar_list_values({datetime_from:server(now-20*60000),datetime_to:server(now+120*60000),limit:1000}));
 if(!calendar.ok||calendar.truncated)throw Error('calendar_unknown');
 let cache={events:[],metadataUTC:'1970-01-01T00:00:00Z'};
 try{cache=JSON.parse(await command("Get-Content -LiteralPath 'E:/GPT/Inves/.skill-tools/rr2-news-cache.json' -Raw"));}catch{}
 const fresh=Date.now()-Date.parse(cache.metadataUTC)<13*60000;
 const ids=[...new Set(calendar.values.map(v=>String(v.event_id)))];
 const results=await Promise.allSettled(ids.map(async id=>{const old=fresh?cache.events.find(e=>String(e.id)===id):null;if(old)return old;const d=parse(await tools.mcp__terminal__economic_calendar_get_event_by_id({event_id:id}));if(!d.ok||!d.event)throw Error('metadata_unknown:'+id);return d.event;}));
 if(results.some(x=>x.status==='rejected'))throw Error('event_metadata_unknown');
 const news={calendar,events:results.map(x=>x.value),metadataUTC:fresh?cache.metadataUTC:new Date().toISOString(),collectedUTC:new Date().toISOString(),offsetMinutes:offset,scope:'global_values_all_dated_event_ids_resolved'};
 const stage=ROOT+'/.skill-tools/rr2_news_stage_'+Date.now()+'.json',path=ROOT+'/trading-journal/rr2_news_'+Date.now()+'.json';
 await tools.apply_patch('*** Begin Patch\n*** Add File: '+stage+'\n+'+JSON.stringify(news)+'\n*** End Patch');
 await command("node 'E:/GPT/Inves/.skill-tools/immutable-json-write.mjs' '"+path+"' '"+stage+"'");
 await command("Copy-Item -LiteralPath '"+path+"' -Destination 'E:/GPT/Inves/.skill-tools/rr2-news-cache.json' -Force");
 return await native("scan '"+plan.path+"'");
})();

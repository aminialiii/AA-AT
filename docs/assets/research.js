"use strict";
/* Research reads a separate warehouse; no broker or worker-control calls. */
const researchState={tab:"explorer",tradeId:null,trades:null,detail:null,performance:null,analysis:null,quality:null,hypotheses:null,status:null,backups:null};
const rEsc=x=>String(x??"—").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c]));
const rNum=(x,d=2)=>x==null?"—":Number(x).toLocaleString("en-US",{maximumFractionDigits:d,minimumFractionDigits:d});
const rMoney=x=>x==null?"—":`${Number(x)<0?"−":"+"}${rNum(Math.abs(Number(x)))}`;
const rPct=x=>x==null?"—":`${rNum(Number(x)*100,1)}%`;
const rWhen=x=>x?new Date(x).toLocaleString():"—";
async function rApi(path,method="GET",body=null){
  const token=sessionStorage.getItem("aaat_token");
  if(!token)throw Error("Sign in to view research.");
  const headers={Authorization:`Bearer ${token}`};
  if(body!==null){headers["Content-Type"]="application/json";headers["X-Idempotency-Key"]=crypto.randomUUID().replaceAll("-","")}
  const response=await fetch(path,{method,headers,body:body===null?undefined:JSON.stringify(body),cache:"no-store"});
  const data=await response.json().catch(()=>({error:"invalid_response"}));
  if(!response.ok)throw Error(data.error||`HTTP ${response.status}`);
  return data;
}
function rTable(headers,rows){
  return `<div class="table-scroll"><table><thead><tr>${headers.map(x=>`<th>${rEsc(x)}</th>`).join("")}</tr></thead><tbody>${rows.join("")}</tbody></table></div>`;
}
function rError(error){document.getElementById("research-content").innerHTML=`<p class="alert">${rEsc(error.message||error)}</p>`}
async function loadResearch(){
  try{
    const [status,performance,analysis,quality,trades,hypotheses]=await Promise.all([
      rApi("/api/research/status"),rApi("/api/research/performance"),
      rApi("/api/research/analysis").catch(()=>null),
      rApi("/api/research/quality"),rApi("/api/research/trades?limit=50"),
      rApi("/api/research/hypotheses")
    ]);
    Object.assign(researchState,{status,performance,analysis,quality,trades,hypotheses});
    document.getElementById("research-cards").innerHTML=[
      ["Verified closes",quality.trades,"One lifecycle per position"],
      ["Attribution unresolved",quality.unresolved_attribution,"Never assigned by Magic Number alone"],
      ["Market candles",quality.market_bars,"Recorded or provenance-tagged"],
      ["Collector",status.stale?"STALE":status.collector.status,rWhen(status.collector.observed_utc)]
    ].map(([a,b,c])=>`<div class="metric"><div class="metric-label">${rEsc(a)}</div><div class="metric-value">${rEsc(b)}</div><div class="metric-foot">${rEsc(c)}</div></div>`).join("");
    renderResearchTab();
  }catch(error){rError(error)}
}
function researchMetricTable(group,first){
  const source=researchState.performance?.[group]||{};
  const rows=Object.entries(source).map(([key,m])=>`<tr><td>${rEsc(key)}</td><td>${m.closed_trades}</td><td>${rPct(m.win_rate)}</td><td>${rMoney(m.net_pnl)}</td><td>${rNum(m.expectancy_r,3)}</td><td>${rNum(m.profit_factor,2)}</td><td>${rMoney(m.max_closed_trade_drawdown_currency)}</td></tr>`);
  return rTable([first,"Closes","Win rate","Net PnL","E[R]","Profit factor","Closed DD"],rows);
}
function researchAnalysisTable(group,first){
  if(!researchState.analysis)return '<p class="subtle">Versioned analytics are unavailable or stale. The broker-reconciled journal remains readable.</p>';
  const source=researchState.analysis?.groups?.[group]||{};
  const rows=Object.entries(source).map(([key,m])=>`<tr><td>${rEsc(key)}</td><td>${m.closed_trades}</td><td>${m.distinct_exit_days}</td><td>${rPct(m.win_rate)}</td><td>${rMoney(m.net_pnl_currency)}</td><td>${rNum(m.expectancy_r,3)}</td><td>${rNum(m.net_profit_factor,2)}</td><td>${rMoney(m.max_closed_trade_drawdown_currency)}</td><td>${rEsc(m.evidence_status)}</td></tr>`);
  return rTable([first,"Closes","Days","Win rate","Net PnL","E[R]","Net PF","Closed DD","Evidence"],rows);
}
function researchRunNote(){
  const a=researchState.analysis;
  if(!a)return '<p class="subtle">Versioned analytics are unavailable; no result is inferred from the journal alone.</p>';
  return `<p class="subtle">Run ${rEsc(a?.analysis_run_id)} · cutoff ${rEsc(a?.cutoff?.last_closed_trade_utc)} · ${rEsc(a?.evidence_class)}. Closed-trade drawdown is not mark-to-market equity drawdown.</p>`;
}
function renderExplorer(){
  const rows=(researchState.trades?.trades||[]).map(t=>`<tr><td><button class="text-link" data-trade-id="${rEsc(t.trade_id)}">${rEsc(t.trade_id.slice(0,10))}</button></td><td>${rEsc(t.strategy_id)}</td><td>${rEsc(t.symbol)}</td><td>${rEsc(t.direction)}</td><td>${rEsc(rWhen(t.exit_utc))}</td><td>${rMoney(t.net_pnl)}</td><td>${rNum(t.realized_r,3)}</td><td>${rEsc(t.attribution_status)}</td></tr>`);
  return `<div class="research-filter"><label>Strategy <select id="r-strategy"><option value="">All</option>${Array.from({length:18},(_,i)=>`<option>S${String(i+1).padStart(2,"0")}</option>`).join("")}</select></label><label>Symbol <input id="r-symbol" placeholder="EURUSD"></label><label>Side <select id="r-direction"><option value="">Both</option><option>BUY</option><option>SELL</option></select></label><label>From <input id="r-start" type="date"></label><label>To <input id="r-end" type="date"></label><button id="r-apply" class="outline small">Apply filters</button></div><p class="subtle">${researchState.trades?.total??0} matching broker-confirmed lifecycles · first ${rows.length} shown</p>${rTable(["Trade","Strategy","Symbol","Side","Exit","Net","R","Attribution"],rows)}`;
}
async function selectTrade(id){
  researchState.tradeId=id;
  researchState.detail=await rApi(`/api/research/trades/${id}`);
  researchState.tab="details";
  renderResearchTab();
}
function renderDetails(){
  const d=researchState.detail;
  if(!d)return '<p class="subtle">Choose a trade in Trade Explorer.</p>';
  const values=[
    ["Trade ID",d.trade_id],["Strategy",d.strategy_id],["Version hash",d.config_sha256],
    ["Symbol / side",`${d.symbol} ${d.direction||"unverified"}`],
    ["Entry UTC",d.entry_utc],["Exit UTC",d.exit_utc],
    ["Initial SL / TP",`${d.initial_sl} / ${d.initial_tp}`],
    ["Opened / closed volume",`${d.opened_volume} / ${d.closed_volume}`],
    ["Gross PnL",d.gross_pnl],["Commission / swap / fees",`${d.commission} / ${d.swap} / ${d.fees}`],
    ["Net PnL",d.net_pnl],["Realized R",d.realized_r],["Attribution",d.attribution_status]
  ];
  const events=(d.position_events||[]).map(e=>`<tr><td>${rEsc(e.kind)}</td><td>${rEsc(e.event_utc)}</td><td>${rEsc(e.volume)}</td><td>${rEsc(e.price)}</td></tr>`);
  return `<div class="research-details">${values.map(([k,v])=>`<div><span>${rEsc(k)}</span><strong>${rEsc(v)}</strong></div>`).join("")}</div><h3>Recorded position events</h3>${rTable(["Kind","Broker time","Volume","Price"],events)}<h3>Data-quality flags</h3><p class="subtle">${(d.quality_issues||[]).map(x=>rEsc(x.code)).join(" · ")||"No flags"}</p>`;
}
function renderResearchTab(){
  document.querySelectorAll("#research-tabs button").forEach(button=>button.classList.toggle("active",button.dataset.researchTab===researchState.tab));
  const box=document.getElementById("research-content"),p=researchState.performance,q=researchState.quality;
  switch(researchState.tab){
    case "explorer":box.innerHTML=renderExplorer();break;
    case "details":box.innerHTML=renderDetails();break;
    case "chart":box.innerHTML=researchState.detail?(researchState.detail.chart_available?`<p>Recorded-candle chart for ${rEsc(researchState.tradeId)}.</p><button id="r-open-chart" class="outline">Load interactive chart</button><div id="r-chart" class="research-chart"></div>`:`<p class="subtle">No recorded market candles cover this trade. A chart or price path would be misleading.</p>`):'<p class="subtle">Choose a trade in Trade Explorer.</p>';break;
    case "strategy":box.innerHTML=researchRunNote()+researchAnalysisTable("strategy","Strategy (mixed versions flagged)");break;
    case "versions":box.innerHTML=researchRunNote()+researchAnalysisTable("strategy_version","Strategy / config SHA-256");break;
    case "symbol":box.innerHTML=researchRunNote()+researchAnalysisTable("strategy_version_symbol","Version / symbol");break;
    case "session":box.innerHTML=researchRunNote()+`<p class="subtle">Session boundaries use London, New York, and Tokyo wall clocks with DST. Sessions may overlap.</p>`+researchAnalysisTable("strategy_version_session","Version / session");break;
    case "time":box.innerHTML=researchRunNote()+`<p class="subtle">UTC entry hour and weekday groups are exploratory; do not select a trading schedule from three exit days.</p><h3>Entry hour UTC</h3>`+researchAnalysisTable("strategy_version_hour_utc","Version / hour")+`<h3>Entry weekday UTC</h3>`+researchAnalysisTable("strategy_version_weekday_utc","Version / weekday");break;
    case "drawdown":box.innerHTML=researchRunNote()+`<p class="subtle">True portfolio equity drawdown: unavailable. Synchronized broker equity observations are insufficient; the values below use closed trade PnL only.</p>`+researchAnalysisTable("strategy_version","Strategy / version")+`<h3>Symbol closed-PnL drawdown</h3>`+researchAnalysisTable("symbol","Symbol");break;
    case "entry":box.innerHTML=`<h2>Entry quality</h2><p class="subtle">Entry Bid/Ask and signal-to-submission timestamps are missing for ${q?.issues?.find(x=>x.code==="entry_bid_ask_missing")?.count??0} trades. No timing-quality conclusion is made from wins or losses alone.</p>`;break;
    case "exit":box.innerHTML=`<h2>Exit quality</h2><p class="subtle">SL/TP modification history and exit Bid/Ask are not in the verified campaign archive. Broker fills and realized PnL remain available in Trade Details.</p>`;break;
    case "excursion":box.innerHTML=`<h2>MFE / MAE</h2><p class="subtle">Trade-level excursion values appear only after recorded tick or candle coverage is imported. OHLC results are explicitly approximate and never assume intrabar order.</p>${researchState.detail?.metrics?`<pre>${rEsc(JSON.stringify(researchState.detail.metrics,null,2))}</pre>`:""}`;break;
    case "management":box.innerHTML=`<h2>Trade-management scenarios</h2><p class="subtle">${rEsc(researchState.analysis?.research_gates?.fill_sensitive_counterfactuals)}. No hypothetical SL, TP, break-even, trailing, partial, or combined outcome is presented as broker performance. TP = 5 is excluded until its unit is documented.</p><p class="subtle">The isolated research engine requires broker-matched Bid/Ask ticks, contract valuation, costs, and a frozen finite scenario horizon.</p>`;break;
    case "costs":box.innerHTML=`<p class="subtle">Broker-recorded commissions, swap, and fees are included in net PnL. Historical spread and slippage require Bid/Ask or quote records.</p>${researchMetricTable("strategy","Strategy")}`;break;
    case "hypotheses":box.innerHTML=(researchState.hypotheses||[]).length?researchState.hypotheses.map(h=>`<article><h3>${rEsc(h.id)} · ${rEsc(h.strategy_id)}</h3><p>${rEsc(h.observed_issue)}</p><small>${rEsc(h.status)}</small></article>`).join(""):'<p class="subtle">No evidence-backed improvement hypothesis has been registered. Example ideas are not findings.</p>';break;
    case "backtest":box.innerHTML=`<h2>One-year historical validation</h2><p class="subtle">${rEsc(researchState.analysis?.research_gates?.one_year_backtest)}. No historical backtest has been run. The proposed half-open period is 2025-10-21 to 2026-10-21 UTC, with chronological 6/3/3-month train/validation/test splits after data and cost verification.</p>`;break;
    case "quality":box.innerHTML=`<p class="subtle">Missing fields stay missing; broker facts and derived metrics remain distinct.</p>${rTable(["Issue","Trades"],(q?.issues||[]).map(x=>`<tr><td>${rEsc(x.code)}</td><td>${x.count}</td></tr>`))}`;break;
  }
}
async function applyResearchFilters(){
  const params=new URLSearchParams({limit:"50"});
  for(const [id,key] of [["r-strategy","strategy"],["r-symbol","symbol"],["r-direction","direction"]]){const value=document.getElementById(id)?.value.trim();if(value)params.set(key,value)}
  const start=document.getElementById("r-start")?.value,end=document.getElementById("r-end")?.value;
  if(start)params.set("start_utc",start+"T00:00:00+00:00");
  if(end)params.set("end_utc",end+"T23:59:59+00:00");
  try{researchState.trades=await rApi("/api/research/trades?"+params);renderResearchTab()}catch(error){toast(error.message,true)}
}
async function openResearchChart(){
  try{
    if(!window.Plotly){
      await new Promise((resolve,reject)=>{const script=document.createElement("script");
        script.src="/assets/plotly.min.js";script.onload=resolve;script.onerror=()=>reject(Error("Chart library unavailable."));document.head.append(script)});
    }
    const fig=await rApi(`/api/research/charts/${researchState.tradeId}.json`);
    await Plotly.newPlot("r-chart",fig.data,fig.layout,{responsive:true,displaylogo:false});
  }catch(error){toast(error.message,true)}
}
async function downloadResearch(){
  try{
    const response=await fetch("/api/research/export",{headers:{Authorization:`Bearer ${sessionStorage.getItem("aaat_token")}`}});
    if(!response.ok)throw Error("Research export unavailable.");
    const url=URL.createObjectURL(await response.blob());
    const link=document.createElement("a");link.href=url;link.download="AA-AT-RESEARCH-DATASET.zip";link.click();
    setTimeout(()=>URL.revokeObjectURL(url),60000);
  }catch(error){toast(error.message,true)}
}
async function loadBackups(){
  try{
    const d=await rApi("/api/backups");researchState.backups=d;
    document.getElementById("backup-cards").innerHTML=[
      ["Worker",d.worker_stale?"STALE":"RUNNING",rWhen(d.heartbeat.observed_utc)],
      ["Last verified",rWhen(d.status.verified_utc),d.status.slot||"No slot"],
      ["Next due",rWhen(d.heartbeat.next_due_utc),"24-hour rotation"],
      ["Free storage",d.available_bytes==null?"—":rNum(d.available_bytes/1073741824,1)+" GB","Outside project/Git"]
    ].map(([a,b,c])=>`<div class="metric"><div class="metric-label">${rEsc(a)}</div><div class="metric-value backup-value">${rEsc(b)}</div><div class="metric-foot">${rEsc(c)}</div></div>`).join("");
    document.getElementById("backup-rows").innerHTML=d.slots.map(s=>`<tr><td>${s.slot}</td><td>${rEsc(rWhen(s.verified_utc))}</td><td>${s.bytes==null?"—":rNum(s.bytes/1048576,1)+" MB"}</td><td>${rEsc(s.verification_status||"EMPTY")}</td></tr>`).join("");
    document.getElementById("backup-observed").textContent=rWhen(d.heartbeat.observed_utc);
    document.getElementById("backup-warning").textContent=d.worker_stale?"Backup worker heartbeat is stale. Previous archives remain preserved.":"Manual backup requests are queued and audited; no restore action is available here.";
    document.getElementById("backup-now").disabled=state.data?.auth_role!=="admin"||d.worker_stale;
  }catch(error){document.getElementById("backup-warning").textContent=error.message}
}
document.querySelectorAll('.nav-link[data-view="research"]').forEach(b=>b.addEventListener("click",()=>{document.getElementById("view-title").textContent="Research journal";loadResearch()}));
document.querySelectorAll('.nav-link[data-view="backups"]').forEach(b=>b.addEventListener("click",()=>{document.getElementById("view-title").textContent="Backup management";loadBackups()}));
document.getElementById("research-tabs").addEventListener("click",e=>{const b=e.target.closest("button[data-research-tab]");if(b){researchState.tab=b.dataset.researchTab;renderResearchTab()}});
document.getElementById("research-content").addEventListener("click",e=>{const trade=e.target.closest("[data-trade-id]");if(trade)selectTrade(trade.dataset.tradeId).catch(x=>toast(x.message,true));if(e.target.id==="r-apply")applyResearchFilters();if(e.target.id==="r-open-chart")openResearchChart()});
document.getElementById("research-export").addEventListener("click",downloadResearch);
document.getElementById("backup-now").addEventListener("click",()=>confirmAction("Create backup now","Queue an independent verified backup? Trading workers will not be restarted.",async()=>{try{const result=await rApi("/api/backups/requests","POST",{});toast(`Backup request ${result.request.id.slice(0,8)} queued.`);setTimeout(loadBackups,1500)}catch(error){toast(error.message,true)}}));
setInterval(()=>{if(state.view==="research")loadResearch();if(state.view==="backups")loadBackups()},60000);

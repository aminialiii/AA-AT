/**
 * Root-owned quiet screen orchestration. Evaluating this source is consequential:
 * it updates workspace calculation input and official MT5 journal/state files.
 * It NEVER sends, closes, modifies, or cancels an order and never edits MT5 settings.
 * Review before invoking with await eval(source) in functions.exec.
 */
(async () => {
  const ROOT = "E:\\GPT\\Inves";
  const MT5 = "C:\\Users\\SOC-Peyman\\AppData\\Roaming\\MetaQuotes\\Terminal\\D0E8209F77C8CF37AD8BF550E51FF075\\MQL5\\Files";
  const STATE = MT5 + "\\Demo_Monitor_State_20261008.json";
  const EVENTS = MT5 + "\\Demo_Execution_Events_20261008.jsonl";
  const INPUT = ROOT + "\\Demo_Screen_Input_20261008.json";
  const OUTPUT = ROOT + "\\Demo_Screen_Output_20261008.json";
  const ANCHOR = ROOT + "\\Demo_Event_Anchor_20261008.json";
  const SYMBOLS = ["EURUSD", "GBPUSD", "XAUUSD"];
  const MIN = 60000, HOUR = 60 * MIN;
  const VERSION = "US_FOMC_RANGE_RETEST_DYNAMIC_RISK_1";
  let stage = "workspace_preflight", statePersisted = false;

  const finite = x => typeof x === "number" && Number.isFinite(x);
  const jsonClone = x => JSON.parse(JSON.stringify(x));
  const equal = (a, b) => JSON.stringify(a) === JSON.stringify(b);
  function fail(code) { const e = new Error(code); e.safeCode = code; throw e; }
  function unpack(result, label) {
    if (!result || result.isError) fail(label + "_tool_error");
    if (result.structuredContent !== undefined) return result.structuredContent;
    const parts = (result.content || []).filter(x => x.type === "text");
    if (parts.length !== 1) fail(label + "_unexpected_content");
    try { return JSON.parse(parts[0].text); } catch { fail(label + "_non_json_response"); }
  }
  function rawText(result, label) {
    if (!result || result.isError) fail(label + "_tool_error");
    const parts = (result.content || []).filter(x => x.type === "text");
    if (parts.length !== 1 || typeof parts[0].text !== "string") fail(label + "_unexpected_content");
    return parts[0].text;
  }
  function finish(status, code, extra = {}) {
    const summary = {status, code, statePersisted, ...extra};
    store("fast_cycle_last_result", summary);
    text(summary);
    return summary;
  }
  async function batch(items) {
    const settled = await Promise.allSettled(items.map(x => x.run()));
    const values = [];
    for (let i = 0; i < settled.length; i++) {
      const item = settled[i];
      if (item.status !== "fulfilled") fail(items[i].label + "_call_failed");
      values.push(items[i].parse(item.value));
    }
    return values;
  }
  const jsonCall = (label, run) => ({label, run, parse: r => unpack(r, label)});
  const textCall = (label, run) => ({label, run, parse: r => rawText(r, label)});
  function shellJson(result, label) {
    if (!result || result.exit_code !== 0 || result.session_id) fail(label + "_shell_failed");
    try { return JSON.parse(result.output.trim()); } catch { fail(label + "_invalid_shell_json"); }
  }
  function serverNaiveMs(s) {
    if (typeof s !== "string") return NaN;
    const m = /^(\d{4})[.-](\d{2})[.-](\d{2})[ T](\d{2}):(\d{2}):(\d{2})(?:\.\d+)?Z?$/.exec(s);
    if (!m) return NaN;
    const t = Date.UTC(+m[1], +m[2] - 1, +m[3], +m[4], +m[5], +m[6]);
    const d = new Date(t);
    return d.getUTCFullYear() === +m[1] && d.getUTCMonth() === +m[2] - 1 &&
      d.getUTCDate() === +m[3] && d.getUTCHours() === +m[4] &&
      d.getUTCMinutes() === +m[5] && d.getUTCSeconds() === +m[6] ? t : NaN;
  }
  function absoluteMs(s) { return typeof s === "string" ? Date.parse(s) : NaN; }
  function offsetOf(time) {
    const utc = absoluteMs(time.utc_time), server = serverNaiveMs(time.trade_server_last_known_time);
    if (!finite(utc) || !finite(server)) fail("official_clock_missing");
    const offset = Math.round((server - utc) / MIN);
    if (Math.abs(offset) > 840 || Math.abs(server - utc - offset * MIN) > 10000)
      fail("server_clock_offset_not_reliable");
    return offset;
  }
  function fnv(account) {
    let value = 2166136261;
    for (const c of account.server + "|" + account.login + "|" + account.currency)
      value = Math.imul(value ^ c.charCodeAt(0), 16777619) >>> 0;
    return value;
  }
  function fingerprintMatches(expected, actual) {
    if (typeof expected === "number") return expected === actual;
    if (typeof expected !== "string") return false;
    return expected === String(actual) || expected.toLowerCase() === actual.toString(16) ||
      expected.toLowerCase() === actual.toString(16).padStart(8, "0") ||
      expected.toLowerCase() === "0x" + actual.toString(16);
  }
  function guardAccount(payload, expected) {
    const a = payload.account, terminal = payload.terminal;
    if (!a || !terminal || String(a.type).toLowerCase() !== "demo" ||
        terminal.server_connected !== true || a.read_only !== false || a.currency !== "USD")
      fail("account_not_connected_writable_usd_demo");
    if (typeof a.server !== "string" || !["string", "number"].includes(typeof a.login) ||
        !finite(a.balance) || !finite(a.equity) || a.equity <= 0 || !finite(a.margin_free))
      fail("account_required_fields_missing");
    if (!fingerprintMatches(expected, fnv(a))) fail("account_fingerprint_mismatch");
    return a;
  }
  function positionCounts(payload) {
    if (!Array.isArray(payload.positions) || !Array.isArray(payload.orders))
      fail("position_order_response_unknown");
    return {positions: payload.positions.length, orders: payload.orders.length};
  }
  function rootsContain(path, roots) {
    const p = path.toLowerCase();
    return Array.isArray(roots) && roots.some(r => {
      const root = String(r).replace(/[\\/]+$/, "").toLowerCase();
      return p === root || p.startsWith(root + "\\") || p.startsWith(root + "/");
    });
  }
  function checkDynamicRules(rules, anchor) {
    if (rules.enabled !== true) fail("entry_rules_disabled");
    if (rules.version !== VERSION || rules.execution_mode !== "controlled_demo_experiment" ||
        rules.research_gate_passed !== false || !equal(rules.symbols, SYMBOLS) ||
        rules.max_simultaneous_positions !== 1 || rules.max_new_entries_this_session !== 4 ||
        rules.active_risk_fraction !== .01 || rules.hard_risk_fraction !== .05 ||
        rules.halt_at_observed_peak_drawdown_fraction !== .02 ||
        rules.halt_after_closed_losses !== 2 ||
        rules.volume_sizing?.mode !== "dynamic_contract_aware" ||
        rules.activation?.next_event_anchor_required !== true)
      fail("dynamic_rules_require_root_review");
    const fields = ["releaseUTC", "windowStartUTC", "windowEndUTC", "entryCutoffUTC", "blocksUTC"];
    if (!anchor || fields.some(k => anchor[k] === undefined)) fail("dynamic_event_anchor_missing");
    const release = absoluteMs(anchor.releaseUTC), start = absoluteMs(anchor.windowStartUTC),
      end = absoluteMs(anchor.windowEndUTC), cutoff = absoluteMs(anchor.entryCutoffUTC);
    if (![release, start, end, cutoff].every(finite) || !(release < start && start < end && end <= cutoff) ||
        !Array.isArray(anchor.blocksUTC) || anchor.blocksUTC.some(pair => !Array.isArray(pair) || pair.length !== 2 ||
          !finite(absoluteMs(pair[0])) || !finite(absoluteMs(pair[1])) || absoluteMs(pair[0]) >= absoluteMs(pair[1])))
      fail("dynamic_event_anchor_order_or_block_invalid");
  }
  const thin = bars => bars.map(b => ({
    ...(b.timeUTC ? {timeUTC: b.timeUTC} : {time: b.time}),
    open: b.open, high: b.high, low: b.low, close: b.close
  }));
  function barOpenUTC(b, offset) {
    return b.timeUTC ? absoluteMs(b.timeUTC) : serverNaiveMs(b.time) - offset * MIN;
  }
  function closedBars(bars, duration, offset, cutoff) {
    if (!Array.isArray(bars)) fail("history_bars_missing");
    return thin(bars).filter(b => {
      const t = barOpenUTC(b, offset);
      if (!finite(t)) fail("history_timestamp_invalid");
      return t + duration <= cutoff;
    });
  }
  function historyRequest(symbol, period, fromUTC, toUTC, offset) {
    // The official tool interprets the supplied range as broker-clock values.
    return tools.mcp__terminal__get_chart_history({
      symbol, period,
      datetime_from: new Date(fromUTC + offset * MIN).toISOString(),
      datetime_to: new Date(toUTC + offset * MIN).toISOString(),
      limit: 500
    });
  }
  function validH1Cache(cache, cutoff, offset) {
    if (!cache || cache.closedBarsOnly !== true || !Array.isArray(cache.bars) ||
        absoluteMs(cache.validUntilUTC) <= cutoff || !finite(absoluteMs(cache.dataAsOfUTC))) return false;
    const oldCutoff = absoluteMs(cache.dataAsOfUTC);
    if (oldCutoff > cutoff || cache.bars.length < 50) return false;
    if (cache.bars.some(b => !finite(barOpenUTC(b, offset)) ||
        barOpenUTC(b, offset) + HOUR > oldCutoff)) return false;
    return barOpenUTC(cache.bars.at(-1), offset) === Math.floor(cutoff / HOUR) * HOUR - HOUR;
  }
  function journalText(result) {
    const textBody = rawText(result, "events_read");
    for (const line of textBody.split(/\r?\n/)) {
      if (!line.trim()) continue;
      try { JSON.parse(line); } catch { fail("events_journal_not_complete_jsonl"); }
    }
    return textBody;
  }

  try {
    // This MUST be the first tool action whenever the helper is invoked.
    const workspace = unpack(await tools.mcp__terminal__get_workspace_info({}), "workspace");
    if (!rootsContain(STATE, workspace.permissions?.read_roots) ||
        !rootsContain(EVENTS, workspace.permissions?.read_roots) ||
        !rootsContain(STATE, workspace.permissions?.write_roots) ||
        !rootsContain(EVENTS, workspace.permissions?.write_roots) ||
        workspace.permissions?.can_modify_files !== true)
      return finish("attention", "official_file_roots_or_modify_permission_missing");

    stage = "fresh_preflight";
    const [time, accountPayload, open, initialState, local] = await batch([
      jsonCall("time", () => tools.mcp__terminal__get_time_information({})),
      jsonCall("account", () => tools.mcp__terminal__get_trading_account_info({})),
      jsonCall("positions", () => tools.mcp__terminal__get_trading_open_positions({include_orders: true})),
      jsonCall("state", () => tools.mcp__terminal__read_file({path: STATE, length: 1000000})),
      {label: "workspace_inputs", run: () => tools.exec_command({
        cmd: "$demoFastRulesText = Get-Content -LiteralPath 'E:\\GPT\\Inves\\Demo_Entry_Rules_20261008_DYNAMIC.json' -Raw\n$demoFastInputText = Get-Content -LiteralPath 'E:\\GPT\\Inves\\Demo_Screen_Input_20261008.json' -Raw\n$demoFastAnchorText = Get-Content -LiteralPath 'E:\\GPT\\Inves\\Demo_Event_Anchor_20261008.json' -Raw\n[pscustomobject]@{rules=($demoFastRulesText | ConvertFrom-Json);inputText=$demoFastInputText;anchor=($demoFastAnchorText | ConvertFrom-Json)} | ConvertTo-Json -Depth 40 -Compress",
        workdir: ROOT, max_output_tokens: 60000
      }), parse: r => shellJson(r, "workspace_inputs")}
    ]);
    if (!initialState || typeof initialState !== "object" || Array.isArray(initialState))
      fail("state_not_json_object");
    const account = guardAccount(accountPayload, initialState.account_fingerprint_fnv1a32);
    const counts = positionCounts(open);
    if (counts.positions || counts.orders)
      return finish("attention", "position_or_order_requires_root_management", counts);
    if (initialState.unknown_execution_outcome || initialState.execution_reconciliation_required ||
        initialState.pending_execution_intent || initialState.pending_order_intent)
      return finish("attention", "execution_reconciliation_required");

    checkDynamicRules(local.rules, local.anchor);
    const offset = offsetOf(time), dataAsOfUTC = time.utc_time, cutoff = absoluteMs(dataAsOfUTC);
    if (!finite(initialState.observed_equity_peak_usd) ||
        !finite(initialState.new_fills_this_session) || !finite(initialState.losses_today))
      fail("state_account_counters_missing");
    let oldInput;
    try { oldInput = JSON.parse(local.inputText); } catch { oldInput = []; }
    if (!Array.isArray(oldInput)) oldInput = [];

    stage = "fresh_M5_H1";
    const oldCaches = initialState.h1_cache || {};
    const nextCaches = jsonClone(oldCaches);
    const neededH1 = SYMBOLS.filter(s => !validH1Cache(oldCaches[s], cutoff, offset));
    const requests = SYMBOLS.map(s => jsonCall(s + "_M5", () =>
      historyRequest(s, "M5", cutoff - 12 * HOUR, cutoff + 5 * MIN, offset)));
    for (const s of neededH1) requests.push(jsonCall(s + "_H1", () =>
      historyRequest(s, "H1", cutoff - 100 * HOUR, cutoff + HOUR, offset)));
    const historyResults = await batch(requests);
    const m5 = {};
    const expectedM5 = Math.floor(cutoff / (5 * MIN)) * 5 * MIN - 5 * MIN;
    for (let i = 0; i < SYMBOLS.length; i++) {
      const symbol = SYMBOLS[i];
      if (historyResults[i].symbol !== symbol || historyResults[i].period !== "M5")
        fail(symbol + "_M5_symbol_period_mismatch");
      m5[symbol] = closedBars(historyResults[i].history, 5 * MIN, offset, cutoff).slice(-125);
      // Retry an incomplete history tail once; never silently evaluate an older last bar.
      if (m5[symbol].length < 100 || barOpenUTC(m5[symbol].at(-1), offset) !== expectedM5) {
        const retry = unpack(await historyRequest(symbol, "M5", cutoff - 12 * HOUR,
          cutoff + 5 * MIN, offset), symbol + "_M5_retry");
        if (retry.symbol !== symbol || retry.period !== "M5") fail(symbol + "_M5_retry_mismatch");
        m5[symbol] = closedBars(retry.history, 5 * MIN, offset, cutoff).slice(-125);
      }
      if (m5[symbol].length < 100 || barOpenUTC(m5[symbol].at(-1), offset) !== expectedM5)
        fail(symbol + "_latest_closed_M5_missing");
    }
    for (let i = 0; i < neededH1.length; i++) {
      const symbol = neededH1[i], data = historyResults[SYMBOLS.length + i];
      if (data.symbol !== symbol || data.period !== "H1") fail(symbol + "_H1_mismatch");
      const bars = closedBars(data.history, HOUR, offset, cutoff).slice(-60);
      if (bars.length < 50 || barOpenUTC(bars.at(-1), offset) !== Math.floor(cutoff / HOUR) * HOUR - HOUR)
        fail(symbol + "_latest_closed_H1_missing");
      nextCaches[symbol] = {closedBarsOnly: true, bars, dataAsOfUTC,
        validUntilUTC: new Date(Math.floor(cutoff / HOUR) * HOUR + HOUR).toISOString()};
    }

    stage = "fresh_quotes";
    const quoteResults = await batch(SYMBOLS.map(s => jsonCall(s + "_quote", () =>
      tools.mcp__terminal__get_marketwatch_symbols({symbol: s, limit: 1}))));
    const peak = Math.max(initialState.observed_equity_peak_usd, account.equity);
    const inputs = SYMBOLS.map((symbol, i) => {
      const rows = quoteResults[i].symbols;
      if (!Array.isArray(rows) || rows.length !== 1 || rows[0].symbol !== symbol)
        fail(symbol + "_quote_symbol_mismatch");
      const source = rows[0];
      const meta = {};
      for (const key of ["symbol", "digits", "point", "contract_size", "currency_profit",
        "volume_min", "volume_max", "volume_step", "trade_stops_level", "trade_freeze_level",
        "trade_mode", "tick_size"]) if (source[key] !== undefined) meta[key] = source[key];
      const quote = {bid: source.bid, ask: source.ask, update_time: source.update_time};
      const checkAccount = {isDemo: true, connected: true, readOnly: false, currency: "USD",
        equity: account.equity, observedPeakEquity: peak, openPositionCount: 0, openOrderCount: 0,
        newEntriesThisSession: initialState.new_fills_this_session, closedLosses: initialState.losses_today,
        unknownExecutionOutcome: false, marginSufficient: false};
      // Conservative FX-only margin estimate; never assume margin for gold.
      const observation = initialState.margin_observation;
      if (symbol !== "XAUUSD" && observation && observation.volume === .01 &&
          finite(observation.actual_margin_usd) && observation.actual_margin_usd > 0 &&
          finite(observation.price) && observation.price > 0 && finite(source.ask)) {
        const marginEstimate = 2 * observation.actual_margin_usd * source.ask / observation.price;
        checkAccount.marginSufficient = account.margin_free > marginEstimate + account.equity * .01;
      }
      return {nowUTC: dataAsOfUTC, dataAsOfUTC, actualServerOffsetMinutes: offset,
        rulesVersion: VERSION, eventAnchor: local.anchor,
        symbol: meta, quote, M5: m5[symbol], M1: [], H1: nextCaches[symbol].bars,
        state: jsonClone(initialState.pending_signals?.[symbol] || {}), account: checkAccount};
    });
    store("fast_cycle_inputs", inputs);
    store("fast_cycle_data_asof", dataAsOfUTC);

    stage = "update_workspace_input";
    const newInputText = JSON.stringify(inputs);
    if (typeof local.inputText !== "string") fail("workspace_old_input_text_missing");
    // UPDATE uses the exact existing body; it will fail instead of deleting/recreating
    // the path or overwriting a concurrently modified file.
    const oldLines = local.inputText.replace(/\r\n/g, "\n").replace(/\n$/, "").split("\n");
    const patch = "*** Begin Patch\n*** Update File: " + INPUT + "\n@@\n" +
      oldLines.map(line => "-" + line).join("\n") + "\n+" + newInputText + "\n*** End Patch";
    const patchResult = await tools.apply_patch(patch);
    const patchDescription = typeof patchResult === "string" ? patchResult : JSON.stringify(patchResult);
    if (/failed|invalid|error|rejected/i.test(patchDescription)) fail("workspace_input_update_failed");

    stage = "pure_cli_evaluation";
    const cli = await tools.exec_command({
      cmd: "& 'C:\\Users\\SOC-Peyman\\AppData\\Local\\hermes\\node\\node.exe' 'E:\\GPT\\Inves\\demo_screen_cli_20261008.mjs'",
      workdir: ROOT, max_output_tokens: 10000
    });
    if (cli.exit_code !== 0 || cli.session_id) fail("pure_cli_evaluation_failed");
    const readOutput = await tools.exec_command({
      cmd: "Get-Content -LiteralPath 'E:\\GPT\\Inves\\Demo_Screen_Output_20261008.json' -Raw",
      workdir: ROOT, max_output_tokens: 20000
    });
    const results = shellJson(readOutput, "pure_cli_output");
    if (!Array.isArray(results) || results.length !== 3) fail("pure_cli_result_count_invalid");
    for (let i = 0; i < results.length; i++) {
      const r = results[i];
      if (r.state?.symbol !== SYMBOLS[i] || r.version !== VERSION ||
          r.dataAsOfUTC !== new Date(cutoff).toISOString() ||
          r.sourceCutoffUTC !== new Date(cutoff).toISOString() ||
          !finite(absoluteMs(r.state.lastEvaluatedUTC)) || absoluteMs(r.state.lastEvaluatedUTC) < cutoff)
        fail("pure_cli_result_identity_or_freshness_mismatch");
    }
    store("fast_cycle_results", results);

    stage = "preserve_and_persist";
    const [lateState, lateAccountPayload, lateOpen] = await batch([
      jsonCall("state_before_write", () => tools.mcp__terminal__read_file({path: STATE, length: 1000000})),
      jsonCall("account_before_write", () => tools.mcp__terminal__get_trading_account_info({})),
      jsonCall("positions_before_write", () => tools.mcp__terminal__get_trading_open_positions({include_orders: true}))
    ]);
    const latestAccount = guardAccount(lateAccountPayload, initialState.account_fingerprint_fnv1a32);
    const lateCounts = positionCounts(lateOpen);
    if (lateCounts.positions || lateCounts.orders)
      return finish("attention", "position_or_order_appeared_no_state_write", lateCounts);
    if (!equal(lateState, initialState))
      return finish("attention", "state_changed_concurrently_no_state_write");
    if (latestAccount.balance !== account.balance || latestAccount.equity !== account.equity)
      return finish("attention", "account_changed_during_screen_no_state_write");
    const nextState = jsonClone(lateState);
    const evaluatedAtUTC = results[0].state.lastEvaluatedUTC;
    const snapshot = {
      utc: evaluatedAtUTC, account_observed_by_utc: time.utc_time,
      dataAsOfUTC, persist_time_utc: new Date().toISOString(),
      balance_usd: account.balance, equity_usd: account.equity, profit_usd: account.profit,
      margin_usd: account.margin, margin_free_usd: account.margin_free,
      open_positions: [], open_orders: [], actual_server_offset_minutes: offset,
      symbols: inputs.map((x, i) => ({symbol: SYMBOLS[i], bid: x.quote.bid, ask: x.quote.ask,
        quote_server_time: x.quote.update_time,
        quote_utc: new Date(serverNaiveMs(x.quote.update_time) - offset * MIN).toISOString(),
        status: results[i].status, reasons: results[i].reasons.map(reason => reason.code),
        SL: null, TP: null, profit_usd: 0}))
    };
    nextState.pending_signals = nextState.pending_signals || {};
    for (let i = 0; i < results.length; i++) nextState.pending_signals[SYMBOLS[i]] = results[i].state;
    nextState.h1_cache = nextCaches;
    nextState.observed_equity_peak_usd = peak;
    nextState.observed_max_drawdown_usd = Math.max(nextState.observed_max_drawdown_usd || 0, peak - account.equity);
    nextState.observed_max_drawdown_percent = Math.max(nextState.observed_max_drawdown_percent || 0,
      100 * (peak - account.equity) / peak);
    nextState.last_snapshot = snapshot;
    nextState.sampled_history_since_cadence_change = nextState.sampled_history_since_cadence_change || [];
    if (!Array.isArray(nextState.sampled_history_since_cadence_change))
      fail("state_sample_history_not_array");
    nextState.sampled_history_since_cadence_change.push(snapshot);
    nextState.last_live_screen_utc = evaluatedAtUTC;
    nextState.last_live_screen_data_asof_utc = dataAsOfUTC;
    nextState.cycle_stage = results.some(r => r.proposal || r.state.active?.retest)
      ? "SCREEN_REQUIRES_ROOT_CONFIRMATION" : "SCREEN_NO_ENTRY_WAIT_FRESH_SETUP";
    const stateWrite = await tools.mcp__terminal__write_file({
      path: STATE, content: JSON.stringify(nextState, null, 2), encoding: "utf-8", overwrite: true, bom: false
    });
    if (!stateWrite || stateWrite.isError) fail("official_state_write_failed");
    statePersisted = true;
    store("fast_cycle_persisted_state", nextState);

    // The terminal file tool protects append-by-replacement of execution journals.
    // Emit an immutable per-cycle shard instead; prior records are never replaced.
    const newEvents = [
      {event: "cycle_snapshot", utc: evaluatedAtUTC, snapshot,
        operational_revision: "OP2_TWO_MINUTE_CYCLE", source: "official_MCP_pure_CLI_fast_screen"},
      ...results.map((r, i) => ({event: "signal_screen", utc: r.state.lastEvaluatedUTC,
        symbol: SYMBOLS[i], dataAsOfUTC, version: VERSION, status: r.status,
        reasons: r.reasons, active: r.state.active, proposal: r.proposal, context: r.context,
        action: "NO_ORDER_HELPER_RETURNS_TO_ROOT"}))
    ];
    const eventShard = MT5 + "\\Demo_Execution_Events_20261008_" +
      evaluatedAtUTC.replace(/[^0-9]/g, "") + ".jsonl";
    const eventsWrite = await tools.mcp__terminal__write_file({
      path: eventShard,
      content: newEvents.map(e => JSON.stringify(e)).join("\n") + "\n",
      encoding: "utf-8", overwrite: false, bom: false
    });
    if (!eventsWrite || eventsWrite.isError) fail("official_events_write_failed_after_state");

    const expectedWaitCodes = new Set(["immutable_range_not_closed", "outside_frozen_entry_window",
      "dynamic_version_requires_fresh_event_anchor"]);
    const attention = results.filter(r => r.status === "pass" || r.proposal || r.state.active?.retest ||
      (r.status === "unknown" &&
       !(r.reasons.length > 0 && r.reasons.every(reason => expectedWaitCodes.has(reason.code)))));
    return finish(attention.length ? "attention" : "quiet",
      attention.length ? "root_confirmation_or_operational_review_required" : "screen_recorded_no_order",
      {dataAsOfUTC, evaluatedAtUTC,
        screens: results.map(r => ({symbol: r.state.symbol, status: r.status,
          reasons: r.reasons.map(x => x.code), active: !!r.state.active,
          retest: !!r.state.active?.retest, proposal: !!r.proposal}))});
  } catch (error) {
    return finish("attention", error.safeCode || "fast_cycle_unexpected_error", {stage});
  }
})()

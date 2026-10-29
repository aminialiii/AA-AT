"""Read-only native gold snapshot and exact deal reconciliation. Never sends orders."""
import sys,json
from pathlib import Path
from datetime import datetime,timezone,timedelta
sys.path.insert(0,'E:/GPT/Inves/.skill-tools')
import MetaTrader5 as mt5
cfg=json.loads(Path('E:/GPT/Inves/Trading_Manager_Config.json').read_text(encoding='utf-8'))
if not mt5.initialize('C:/Program Files/MetaTrader 5/terminal64.exe',timeout=5000):raise RuntimeError(str(mt5.last_error()))
try:
 a,t=mt5.account_info(),mt5.terminal_info()
 if a is None or t is None or str(a.login)!=cfg['account_login'] or a.server!=cfg['account_server'] or a.currency!='USD' or a.trade_mode!=mt5.ACCOUNT_TRADE_MODE_DEMO or not t.connected:raise RuntimeError('account_gate')
 positions,orders=mt5.positions_get(),mt5.orders_get()
 if positions is None or orders is None:raise RuntimeError('exposure_unknown')
 now=datetime.now(timezone.utc);offset=cfg['broker_UTC_offset_minutes'];servernow=now+timedelta(minutes=offset)
 s,q=mt5.symbol_info('XAUUSD'),mt5.symbol_info_tick('XAUUSD')
 if s is None or q is None or not s.visible or s.trade_mode!=mt5.SYMBOL_TRADE_MODE_FULL:raise RuntimeError('symbol_gate')
 ticks=mt5.copy_ticks_range('XAUUSD',servernow-timedelta(minutes=cfg['tick_history_minutes']),servernow,mt5.COPY_TICKS_ALL)
 if ticks is None:raise RuntimeError('ticks_unknown')
 out=dict(observedUTC=now.isoformat(),offsetMinutes=offset,account=a._asdict(),terminal=t._asdict(),positions=[x._asdict() for x in positions],orders=[x._asdict() for x in orders],symbol=s._asdict(),tick=q._asdict(),ticks=[dict(time_ms=datetime.fromtimestamp(int(x['time_msc'])/1000,timezone.utc).isoformat(timespec='milliseconds').replace('+00:00',''),bid=float(x['bid']),ask=float(x['ask'])) for x in ticks],source='native_read_only')
 if len(sys.argv)>1 and sys.argv[1]!='-':
  ticket=int(sys.argv[1]);deals=mt5.history_deals_get(position=ticket)
  if deals is None:raise RuntimeError('deals_unknown')
  out['reconciliation']=dict(position_id=str(ticket),deals=[x._asdict() for x in deals])
 record=Path('E:/GPT/Inves/trading-journal')/('gold_native_snapshot_'+now.strftime('%Y%m%dT%H%M%S%fZ')+'.json')
 with record.open('x',encoding='utf-8') as f:json.dump(out,f)
 print(json.dumps(dict(snapshotPath=str(record),observedUTC=out['observedUTC'],account=out['account'],positions=out['positions'],orders=out['orders'],tick=out['tick'],tickCount=len(out['ticks']),firstTick=out['ticks'][0] if out['ticks'] else None,lastTick=out['ticks'][-1] if out['ticks'] else None,reconciliation=out.get('reconciliation'))))
finally:mt5.shutdown()

"""Read-only native M1 history/profit/margin probe. No orders/settings/account switching."""
import sys,json,hashlib
from pathlib import Path
from datetime import datetime,timezone,timedelta
sys.path.insert(0,'E:/GPT/Inves/.skill-tools')
import MetaTrader5 as mt5
root=Path('E:/GPT/Inves/research/poursamadi-backtest')
cfg=json.loads(Path('E:/GPT/Inves/Trading_Manager_Config.json').read_text(encoding='utf-8'))
model=json.loads((root/'model-v1.json').read_text(encoding='utf-8'))
if not mt5.initialize('C:/Program Files/MetaTrader 5/terminal64.exe',timeout=5000):raise RuntimeError(str(mt5.last_error()))
try:
 a,t=mt5.account_info(),mt5.terminal_info()
 if a is None or t is None or str(a.login)!=cfg['account_login'] or a.server!=cfg['account_server'] or a.trade_mode!=mt5.ACCOUNT_TRADE_MODE_DEMO or a.currency!='USD' or not t.connected:raise RuntimeError('account_gate')
 positions,orders=mt5.positions_get(),mt5.orders_get()
 if positions is None or orders is None:raise RuntimeError('exposure_unknown')
 s=mt5.symbol_info('XAUUSD');q=mt5.symbol_info_tick('XAUUSD')
 if s is None or q is None or not s.visible or s.trade_mode!=mt5.SYMBOL_TRADE_MODE_FULL:raise RuntimeError('symbol_gate')
 offset=cfg['broker_UTC_offset_minutes']
 start=datetime.fromisoformat(model['split']['trainFromUTC'].replace('Z','+00:00'))
 end=datetime.fromisoformat(model['split']['testToUTC'].replace('Z','+00:00'))
 rates=mt5.copy_rates_range('XAUUSD',mt5.TIMEFRAME_M1,start+timedelta(minutes=offset),end+timedelta(minutes=offset))
 if rates is None:raise RuntimeError('rates_unknown:'+str(mt5.last_error()))
 bars=[dict(t=int(x['time'])*1000-offset*60000,open=float(x['open']),high=float(x['high']),low=float(x['low']),close=float(x['close']),tick_volume=int(x['tick_volume']),spread=int(x['spread'])) for x in rates if start.timestamp()*1000<=int(x['time'])*1000-offset*60000<end.timestamp()*1000]
 bars.sort(key=lambda x:x['t'])
 profit=mt5.order_calc_profit(mt5.ORDER_TYPE_BUY,'XAUUSD',s.volume_min,q.ask,q.ask-1)
 margin=mt5.order_calc_margin(mt5.ORDER_TYPE_BUY,'XAUUSD',s.volume_min,q.ask)
 out=dict(collectedUTC=datetime.now(timezone.utc).isoformat(),modelVersion=model['version'],source='native_MT5_copy_rates_range',brokerOffsetMinutes=offset,offsetLimitation='Current measured offset applied to September-October history; historical server DST regime not independently reconstructed.',requestedStartUTC=start.isoformat(),requestedEndUTC=end.isoformat(),account=a._asdict(),terminal=t._asdict(),positions=[x._asdict() for x in positions],orders=[x._asdict() for x in orders],symbol=s._asdict(),tick=q._asdict(),nativeProbe=dict(volume=s.volume_min,entry=q.ask,onePriceUnitProfit=profit,margin=margin),bars=bars)
 path=root/('native_m1_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.json')
 with path.open('x',encoding='utf-8') as f:json.dump(out,f,separators=(',',':'))
 digest=hashlib.sha256(path.read_bytes()).hexdigest()
 print(json.dumps(dict(path=str(path),sha256=digest,bars=len(bars),firstUTC=datetime.fromtimestamp(bars[0]['t']/1000,timezone.utc).isoformat() if bars else None,lastUTC=datetime.fromtimestamp(bars[-1]['t']/1000,timezone.utc).isoformat() if bars else None,nativeProbe=out['nativeProbe'],positions=out['positions'],orders=out['orders'])))
finally:mt5.shutdown()

"""Research identity and expiry models, never connected to a broker."""
import hashlib,json
def research_model_identity(model,timeframe):
 if timeframe not in {'M1','M5','TICKS','S5','S15'}:raise ValueError('explicit supported timeframe required')
 item={k:v for k,v in model.items() if k!='id'};item['timeframe']=timeframe
 return 'EDU32_'+hashlib.sha256(json.dumps(item,sort_keys=True).encode()).hexdigest()[:16]
def expiry_outcome(fill_seconds,manager_cancel_seconds=None,broker_expiry_seconds=None):
 """Cancel wins only if it became effective by fill. No atomicity is assumed."""
 deadlines=[x for x in [manager_cancel_seconds,broker_expiry_seconds] if x is not None]
 if deadlines and min(deadlines)<=fill_seconds:return 'CANCELLED_OR_EXPIRED'
 return 'FILLED_LATE' if fill_seconds>45 else 'FILLED'

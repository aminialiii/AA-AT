// AA-AT V3 historical research only. Never attach to an online chart.
// Frozen Python source SHA-256:
// 7858325bc531382b52bdb9e5fdc910b44cf7ebfe6bea19934e24faafd618ebfb
// Strategy: S04 M1_MOMENTUM_PROXY, model OR1_40091e532162.
// The signal rule is the frozen Python signal; tester fills are a separately
// labeled execution model and are not claimed to match M1 bar replay fills.
#property strict
#property version   "2.00"
#property description "S04 tester-only completed-M1 momentum proxy"

input double InpBodyATR = 0.20;
input double InpMinStopATR = 0.50;
input double InpTargetR = 2.00;
input bool InpSignalOnly = true;
input bool InpParityTrace = false; // Research tester diagnostic; no orders.
input long InpMagic = 26102104;

datetime last_forming_bar = 0;

double Max3(double a, double b, double c)
  {
   return MathMax(a, MathMax(b,c));
  }

bool TesterOnly()
  {
   return MQLInfoInteger(MQL_TESTER) != 0;
  }

int OnInit()
  {
   // Hard guard at initialization and again before any simulated order call.
   if(!TesterOnly())
     {
      Print("AAAT_V3_RESEARCH_ONLY: refuse execution outside Strategy Tester");
      return INIT_FAILED;
     }
   // Even tester-only orders require an explicitly classified research DEMO.
   if(AccountInfoInteger(ACCOUNT_TRADE_MODE) != ACCOUNT_TRADE_MODE_DEMO)
     {
      Print("AAAT_V3_RESEARCH_ONLY: DEMO account classification required");
      return INIT_FAILED;
     }
   if(InpBodyATR <= 0.0 || InpMinStopATR <= 0.0 || InpTargetR != 2.0)
      return INIT_PARAMETERS_INCORRECT;
   if(_Period != PERIOD_M1)
      return INIT_PARAMETERS_INCORRECT;
   return INIT_SUCCEEDED;
  }

// The source uses a trailing arithmetic mean of 14 true ranges, not Wilder ATR.
// rates[] is physically oldest-first, as returned by CopyRates.
double ArithmeticATR14(MqlRates &rates[], int n)
  {
   double sum = 0.0;
   for(int i=n-14; i<n; ++i)
     {
      double previous_close = rates[i-1].close;
      sum += Max3(rates[i].high-rates[i].low,
                  MathAbs(rates[i].high-previous_close),
                  MathAbs(rates[i].low-previous_close));
     }
   return sum/14.0;
  }

bool CompletedBarsReady(MqlRates &rates[], int n)
  {
   // Live adapter requires 260 rates, including the forming bar.
   if(n < 259)
      return false;
   // Original valid[] quarantines the first 100 bars and 100 after each gap.
   for(int i=n-100; i<n; ++i)
      if(rates[i].time-rates[i-1].time != 60)
         return false;
   return true;
  }

int S04Signal(MqlRates &rates[], int n, double atr)
  {
   if(atr <= 0.0)
      return 0;
   const double body = (rates[n-1].close-rates[n-1].open)/atr;
   if(body >= InpBodyATR && rates[n-1].close > rates[n-2].close)
      return 1;
   if(body <= -InpBodyATR && rates[n-1].close < rates[n-2].close)
      return -1;
   return 0;
  }

double PreviousSpreadModel(MqlRates &rates[], int n, double point, double tick)
  {
   // Previous five completed bars exclude the signal bar, then 1.25x reserve.
   double maximum = 0.0;
   for(int i=n-6; i<=n-2; ++i)
      maximum = MathMax(maximum, (double)rates[i].spread*point);
   return MathMax(maximum,tick)*1.25;
  }

double TargetForAccountRisk(int side, double volume, double entry,
                            double risk, double tick, int digits)
  {
   ENUM_ORDER_TYPE kind = (side > 0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   double lower = tick;
   double upper = MathMax(8.0*tick, 8.0*risk/
                         MathMax(volume*SymbolInfoDouble(_Symbol,SYMBOL_TRADE_CONTRACT_SIZE),tick));
   double payoff = 0.0;
   for(int extend=0; extend<30; ++extend)
     {
      double candidate = entry + side*upper;
      if(candidate <= 0.0 || !OrderCalcProfit(kind,_Symbol,volume,entry,candidate,payoff))
         return 0.0;
      if(payoff >= InpTargetR*risk)
         break;
      upper *= 2.0;
     }
   if(payoff < InpTargetR*risk)
      return 0.0;
   for(int i=0; i<45; ++i)
     {
      double middle=(lower+upper)/2.0;
      if(!OrderCalcProfit(kind,_Symbol,volume,entry,entry+side*middle,payoff))
         return 0.0;
      if(payoff >= InpTargetR*risk)
         upper=middle;
      else
         lower=middle;
     }
   double raw=entry+side*upper;
   double rounded=(side>0 ? MathCeil(raw/tick-1.0e-8) :
                              MathFloor(raw/tick+1.0e-8))*tick;
   return NormalizeDouble(rounded,digits);
  }

void OnTick()
  {
   if(!TesterOnly())
      return;
   datetime forming=iTime(_Symbol,PERIOD_M1,0);
   if(forming <= 0 || forming == last_forming_bar)
      return;
   last_forming_bar=forming;
   MqlRates rates[];
   // The live broker adapter requests 500 rates (499 completed + forming).
   int n=CopyRates(_Symbol,PERIOD_M1,1,499,rates);
   if(!CompletedBarsReady(rates,n))
      return;
   if(rates[n-1].time+60 != forming)
      return;
   double tick_size=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);
   double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   int digits=(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS);
   if(tick_size <= 0.0 || point <= 0.0)
      return;
   double atr=MathMax(ArithmeticATR14(rates,n),tick_size);
   int side=S04Signal(rates,n,atr);
   double modeled_spread=PreviousSpreadModel(rates,n,point,tick_size);
   MqlTick quote;
   if(!SymbolInfoTick(_Symbol,quote) || quote.bid <= 0.0 || quote.ask < quote.bid)
      return;
   double live_spread=quote.ask-quote.bid;
   bool eligible=(side != 0 && live_spread/atr <= 0.25);
   if(InpParityTrace)
      PrintFormat("AAAT_V3_TRACE,S04,%s,%s,%d,%.12f,%.12f,%.12f,%d",
                  _Symbol,TimeToString(rates[n-1].time,TIME_DATE|TIME_SECONDS),
                  side,atr,modeled_spread,live_spread,(int)eligible);
   if(side == 0)
      return;
   if(live_spread/atr > 0.25)
      return;
   PrintFormat("AAAT_V3_SIGNAL,S04,%s,%s,%d,%.10f,%.10f",
               _Symbol,TimeToString(rates[n-1].time,TIME_DATE|TIME_SECONDS),
               side,atr,modeled_spread);
   double entry=(side>0 ? quote.ask : quote.bid);
   double volume=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   if(volume <= 0.0)
      return;
   double minimum=Max3(InpMinStopATR*atr,4.0*live_spread,
                       (double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*point);
   double low=Max3(-rates[n-1].low,-rates[n-2].low,-rates[n-3].low)*-1.0;
   double high=Max3(rates[n-1].high,rates[n-2].high,rates[n-3].high);
   double raw_sl=(side>0 ? MathMin(low-2.0*tick_size,entry-minimum) :
                            MathMax(high+live_spread+2.0*tick_size,entry+minimum));
   double sl=(side>0 ? MathFloor(raw_sl/tick_size+1.0e-8) :
                        MathCeil(raw_sl/tick_size-1.0e-8))*tick_size;
   sl=NormalizeDouble(sl,digits);
   double loss=0.0;
   ENUM_ORDER_TYPE kind=(side>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   if(!OrderCalcProfit(kind,_Symbol,volume,entry,sl,loss) || loss >= 0.0)
      return;
   double tp=TargetForAccountRisk(side,volume,entry,-loss,tick_size,digits);
   if(tp <= 0.0)
      return;
   if(InpParityTrace)
      PrintFormat("AAAT_V3_LEVELS,S04,%s,%s,%d,%.12f,%.12f,%.12f,%.8f,%.8f",
                  _Symbol,TimeToString(rates[n-1].time,TIME_DATE|TIME_SECONDS),
                  side,entry,sl,tp,volume,-loss);
   if(InpSignalOnly || PositionSelect(_Symbol))
      return;
   if(!TesterOnly())
      return;
   // All order calls below run only inside the isolated Strategy Tester.
   MqlTradeRequest request={};
   MqlTradeResult result={};
   request.action=TRADE_ACTION_DEAL;
   request.symbol=_Symbol;
   request.volume=volume;
   request.type=kind;
   request.price=entry;
   request.sl=sl;
   request.tp=tp;
   request.deviation=5;
   request.magic=(ulong)InpMagic;
   request.comment="AAAT-V3-S04-TEST";
   request.type_filling=ORDER_FILLING_FOK;
   request.type_time=ORDER_TIME_GTC;
   bool sent=OrderSend(request,result);
   PrintFormat("AAAT_V3_TESTER_SEND,S04,%s,%d,%.8f,%.8f,%.8f,%d,%d",
               _Symbol,side,entry,sl,tp,(int)sent,(int)result.retcode);
  }

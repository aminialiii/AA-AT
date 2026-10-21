#property strict
#property script_show_inputs
input string OutputTag="initial";
void OnStart(){
 string symbols[]={"EURUSD","GBPUSD","AUDUSD","NZDUSD"};
 string body="{\"login\":\""+IntegerToString(AccountInfoInteger(ACCOUNT_LOGIN))+"\",\"server\":\""+AccountInfoString(ACCOUNT_SERVER)+"\",\"observedUTC\":\""+TimeToString(TimeGMT(),TIME_DATE|TIME_SECONDS)+"\",\"leverage\":"+IntegerToString(AccountInfoInteger(ACCOUNT_LEVERAGE))+",\"rows\":[";
 bool first=true;
 for(int s=0;s<ArraySize(symbols);s++){
  MqlTick tick;if(!SymbolInfoTick(symbols[s],tick))continue;
  for(int v=1;v<=10;v++)for(int side=0;side<=1;side++){
   double volume=v*.01,margin=0,price=side==0?tick.ask:tick.bid;ENUM_ORDER_TYPE type=side==0?ORDER_TYPE_BUY:ORDER_TYPE_SELL;
   bool ok=OrderCalcMargin(type,symbols[s],volume,price,margin);
   if(!first)body+=",";first=false;
   body+="{\"symbol\":\""+symbols[s]+"\",\"side\":\""+(side==0?"buy":"sell")+"\",\"volume\":"+DoubleToString(volume,2)+",\"price\":"+DoubleToString(price,5)+",\"margin\":"+DoubleToString(margin,8)+",\"ok\":"+(ok?"true":"false")+"}";
  }
 }
 body+="]}";
 string filename="TradingRiskProbe_"+OutputTag+".json";
 if(FileIsExist(filename)){Print("Refusing to overwrite ",filename);return;}
 int handle=FileOpen(filename,FILE_WRITE|FILE_TXT|FILE_ANSI);if(handle==INVALID_HANDLE){Print("File error ",GetLastError());return;}FileWriteString(handle,body);FileClose(handle);Print("Read-only native margin probe saved: ",filename);
}

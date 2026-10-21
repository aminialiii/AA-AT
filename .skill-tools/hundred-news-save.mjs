import fs from 'node:fs';
const data=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));
if(!data.calendar?.ok||data.calendar?.truncated||!data.events?.ok)throw Error('incomplete_calendar');
fs.writeFileSync('E:/GPT/Inves/trading-journal/hundred_news_'+Date.now()+'.json',JSON.stringify(data),{flag:'wx'});
fs.writeFileSync('E:/GPT/Inves/.skill-tools/hundred-news-cache.json',JSON.stringify(data));
console.log(JSON.stringify({ok:true,values:data.calendar.count,events:data.events.events.length,collectedUTC:data.collectedUTC}));

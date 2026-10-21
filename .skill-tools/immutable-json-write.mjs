import fs from 'node:fs';
import path from 'node:path';
const root=path.resolve('E:/GPT/Inves/trading-journal');
const target=path.resolve(process.argv[2]);
const relative=path.relative(root,target);
if(!relative || relative.startsWith('..') || path.isAbsolute(relative) || path.extname(target)!=='.json') throw Error('journal_path_rejected');
let raw;
if(process.argv[3]){
 const stagingRoot=path.resolve('E:/GPT/Inves/.skill-tools');
 const input=path.resolve(process.argv[3]);
 const inputRelative=path.relative(stagingRoot,input);
 if(!inputRelative || inputRelative.startsWith('..') || path.isAbsolute(inputRelative) || path.extname(input)!=='.json')throw Error('staging_path_rejected');
 raw=fs.readFileSync(input,'utf8');
}else{
 const chunks=[];for await(const chunk of process.stdin)chunks.push(chunk);
 raw=Buffer.concat(chunks).toString('utf8');
}
const value=JSON.parse(raw);
fs.writeFileSync(target,JSON.stringify(value,null,2),{flag:'wx'});
console.log(JSON.stringify({created:target,mode:'exclusive'}));

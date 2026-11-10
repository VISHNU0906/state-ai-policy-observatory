'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const root=path.join(__dirname,'..');
const context={window:{},document:{getElementById:()=>({})}};
vm.createContext(context);
vm.runInContext(fs.readFileSync(path.join(root,'dist/app.js'),'utf8'),context);
const data=JSON.parse(fs.readFileSync(path.join(root,'data/events.json'),'utf8'));
const actual=[...data.events].reverse().sort(context.compareEvents).map(e=>e.id);
assert.deepEqual(actual,data.events.map(e=>e.id),'Dashboard and CSV build must agree');
const dates=[['unknown',null],['year','2025'],['month','2025-01'],['day','2025-01-01']];
const fixtures=dates.map(([date_precision,event_date],i)=>({date_precision,event_date,state:'Kerala',id:String(i)}));
for(const order of ['newest','oldest','state']){
  assert.deepEqual([...fixtures].sort((a,b)=>context.compareEvents(a,b,order)).map(e=>e.date_precision),['day','month','year','unknown']);
}
console.log('Dashboard ordering matches the dataset; partial and unknown dates passed all three sort modes.');

import {render as prender} from '/workspace/frontend/src/pages/proposals.js';
import {render as arender} from '/workspace/frontend/src/pages/aliases.js';
const d={
 entrances:[{id:1,code:'CQ-018-A',street:'长桥路',number:18,label:'正门',lat:31.21,lng:121.48},
            {id:2,code:'CQ-018-B',street:'长桥路',number:18,label:'旧门牌',lat:31.2101,lng:121.48}],
 aliases:[{id:1,entrance_id:1,text:'长桥路18号正门',state:'verified'},
          {id:2,entrance_id:2,text:'长桥路十八号旧门牌',state:'verified'},
          {id:3,entrance_id:2,text:'长桥路十十号旧称',state:'pending_fix'}],
 evidence:[{alias_id:1,reference:'照片-A',description:'现场核验说明足够长的文字'},
           {alias_id:2,reference:'照片-B',description:'现场核验说明足够长的文字'},
           {alias_id:3,reference:'旧档-B',description:'誊抄件待补正的现场核验说明文字'}],
 runs:[{id:1,state:'superseded',revision:0,result:{bad_aliases:[{alias_id:3,bad_tokens:['十十号']}],evaluation:{precision:1,recall:1,train_pairs:36,holdout_pairs:12,threshold:0.55,label_source:'模拟'}}},
       {id:2,state:'ready',revision:1,result:{bad_aliases:[],evaluation:{precision:1,recall:1,train_pairs:36,holdout_pairs:12,threshold:0.55,label_source:'模拟'}}}],
 candidates:[{run_id:2,source_id:1,target_id:2,similarity:0.83,conflict:0,pending:0,missed_alias_ids:[]},
             {run_id:1,source_id:1,target_id:2,similarity:0.71,conflict:0,pending:1,missed_alias_ids:[3]}],
 proposals:[{id:1,code:'P031',source_id:2,target_id:1,reason:'历史同宗同入口的现场核验依据文字',state:'draft'}],
 clock:[{now:'2026-11-18T09:00:00',revision:1}],objections:[],notices:[],redirects:[]};
const html=prender(d);
for(const k of ['坏别名','待补','暂用分','当前修订号 1','批次 #2','长桥路十十号旧称','/aliases/3','PATCH'])
 if(!html.includes(k))throw new Error('missing '+k);
// 当前批次无待补行：不应出现 row-pending
if(html.includes('row-pending'))throw new Error('current run should have no pending row');
// 脱版场景：现行修订号高于最新 ready 批次
const stale=JSON.parse(JSON.stringify(d));stale.clock[0].revision=2;
const h2=prender(stale);
for(const k of ['资料已变更，请重新计算','已脱版，旧分与待补状态不能当作补正后的结果'])
 if(!h2.includes(k))throw new Error('stale missing '+k);
// 待补场景：最新 ready 批次含 pending
const pend=JSON.parse(JSON.stringify(d));pend.runs=pend.runs.filter(r=>r.id===1).map(r=>({...r,state:'ready'}));pend.candidates=pend.candidates.filter(c=>c.run_id===1);pend.clock[0].revision=0;
const h3=prender(pend);
for(const k of ['row-pending','待补 · 漏比别名 #3','0.710'])
 if(!h3.includes(k))throw new Error('pending missing '+k);
// 别名页徽标
const ah=arender(d);
if(!ah.includes('待补正')||!ah.includes('已核验'))throw new Error('alias badges missing');
console.log('FRONTEND RENDER TESTS PASSED');

import{heading,form,input,select,area,badge}from'../components/registry.js';
import{opts,esc}from'../utils/format.js';
function runView(d){
 let rev=d.clock[0].revision??0,ready=d.runs.filter(x=>x.state==='ready');
 let current=ready.filter(x=>(x.revision??0)===rev).at(-1)||null;
 let latest=d.runs.at(-1)||null;
 return {rev,current,latest,stale:!!latest&&latest.state==='ready'&&!current};
}
function badAliasSection(d,view){
 let bad=d.aliases.filter(a=>a.state==='pending_fix');
 if(!bad.length)return '<h2>坏别名</h2><p>暂无待补正别名。</p>';
 return `<h2>坏别名 · 留待补正（${bad.length}）</h2>${bad.map(a=>{let e=d.entrances.find(x=>x.id===a.entrance_id);let tokens=(view.current?.result?.bad_aliases||view.latest?.result?.bad_aliases||[]).find(b=>b.alias_id===a.id)?.bad_tokens||[];return `<article class="bad-alias">${badge(a.state)}<h3>${esc(a.text)}</h3><p>所属入口：${esc(e?e.code+' / '+e.label:('#'+a.entrance_id))}${tokens.length?` · 坏门牌语：${esc(tokens.join('、'))}`:''}</p>${form('alias-fix-'+a.id,'补正坏别名','/aliases/'+a.id,input('text','更正后的别名原文','长桥路十八号旧称'),'PATCH')}</article>`}).join('')}`;
}
export function render(d){
 let view=runView(d),run=view.current||view.latest,ev=run?.result?.evaluation;
 let rows=d.candidates.filter(c=>c.run_id===run?.id);
 let ent=id=>d.entrances.find(e=>e.id===id);
 return heading('03','近似名字，先过数字关。','坏别名不再拖垮整批：能算的门牌对照常出暂用分；漏比坏别名的门牌对一律待补，有分也不得立案，补正重算后旧批次脱版。')+`<div class="split"><section><button data-action="/matches">计算别名归并候选</button>${run?badge(run.state):''}${view.stale?'<span class="badge pending_fix">资料已变更，请重新计算</span>':''}${ev?`<p>留出精确率 ${ev.precision.toFixed(3)} / 召回率 ${ev.recall.toFixed(3)} · 训练 ${ev.train_pairs} 对 / 留出 ${ev.holdout_pairs} 对</p><small>seed42 · 训练选择阈值 ${ev.threshold} · ${esc(ev.label_source)}</small>`:''}${run?.error?`<p class="error">${esc(run.error)}，可补别名后重新计算。</p>`:''}${view.current?`<small>当前修订号 ${view.rev} · 批次 #${view.current.id} 与现行资料一致</small>`:(run?`<small class="error">批次 #${run.id} 已脱版，旧分与待补状态不能当作补正后的结果。</small>`:'')}
${badAliasSection(d,view)}
<h2>门牌对核验（暂用分与待补）</h2>
<table><thead><tr><th>来源 → 目标</th><th>余弦暂用分</th><th>数字核验</th><th>状态</th></tr></thead><tbody>${rows.map(c=>`<tr class="${c.pending?'row-pending':''}"><td>${ent(c.source_id)?.code} → ${ent(c.target_id)?.code}</td><td>${c.similarity==null?'—':c.similarity.toFixed(3)}</td><td>${c.conflict?'数字冲突 / 禁归并':'可人工复核'}</td><td>${c.pending?`待补 · 漏比别名 #${(c.missed_alias_ids||[]).join('、#')}`:'正常'}</td></tr>`).join('')||'<tr><td colspan="4">尚无已计算批次。</td></tr>'}</tbody></table>
<h2>核定提案簿</h2>${d.proposals.map(x=>`<article><b>${esc(x.code)}</b> ${badge(x.state)}<p>入口 #${x.source_id} → #${x.target_id}</p><p>${esc(x.reason)}</p></article>`).join('')}</section><aside>${form('proposal-create','形成归并提案','/proposals',input('code','提案编号','P-UI-01')+select('source_id','待归并入口',opts(d.entrances,x=>x.code+' / '+x.label))+select('target_id','归并目标',opts(d.entrances,x=>x.code+' / '+x.label))+area('reason','门牌及权属核验依据','现场两位采集员核对门牌照片与地籍图，确认为同一入口'))}<p class="evidence">待补门牌对即使已有暂用分，后端也拒绝立案；补正坏别名并重新计算后才可提案。</p></aside></div>`}

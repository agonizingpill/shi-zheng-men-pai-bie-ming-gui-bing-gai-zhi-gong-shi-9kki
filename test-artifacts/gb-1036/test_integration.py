import os,pathlib
TDIR=pathlib.Path('/tmp/addr-test');TDIR.mkdir(exist_ok=True)
os.environ['DATABASE_URL']='sqlite:///'+str(TDIR/'test.db')
os.environ['REDIS_URL']='redis://localhost:6399/0'
os.environ['JWT_SECRET']='test-secret'
os.environ['SEED_DEMO']='false'
import sys;sys.path.insert(0,'/workspace/backend')
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src import database as db
db.engine=create_engine(os.environ['DATABASE_URL'])
db.Session=sessionmaker(db.engine,expire_on_commit=False)
from fastapi import HTTPException
from src.database import Session,Base,engine
from src import models
from src.models import *
from src.common import rows
from src.worker import process_run
from src.matching import alias_quality
from src import entrance_service,proposal_service
from scripts.seed_demo import seed
if os.path.exists(TDIR/'test.db'):os.remove(TDIR/'test.db')
Base.metadata.create_all(engine)
seed()
with Session() as s:
 reg=s.get(Registry,1);assert reg.revision==0
 ent={e.code:e for e in rows(s,Entrance)}
 B,A,C=ent['CQ-018-B'],ent['CQ-018-A'],ent['CQ-081']
 bad=[a for a in rows(s,Alias) if '十十' in a.text];assert len(bad)==1
 bad_id=bad[0].id
 # --- 第一批匹配（含坏别名，整批不报错）---
 run=MatchRun(state='queued');s.add(run);s.flush();rid1=run.id
 process_run(s,rid1);s.commit()
 run=s.get(MatchRun,rid1);assert run.state=='ready',run.error
 assert run.revision==0
 bad_alias=s.get(Alias,bad_id);assert bad_alias.state=='pending_fix'
 assert [b['alias_id'] for b in run.result['bad_aliases']]==[bad_id]
 cands={(c.source_id,c.target_id):c for c in rows(s,Candidate) if c.run_id==rid1}
 assert len(cands)==6  # 4 入口 6 个门牌对全部落库
 key=(A.id,B.id) if (A.id,B.id) in cands else (B.id,A.id)
 cBA=cands[key];assert cBA.pending==1 and bad_id in cBA.missed_alias_ids and cBA.similarity is not None
 assert all((v.pending==1)==(bad_id in v.missed_alias_ids) for v in cands.values())
 print('1) 坏别名隔离+待补+暂用分 ok')
 # --- 发布重试不重复出候选：同批次重放不新增，候选唯一约束兜底 ---
 before=len(rows(s,Candidate))
 process_run(s,rid1);s.commit()  # state 已不是 queued，应空转
 assert len(rows(s,Candidate))==before
 try:
  s.add(Candidate(run_id=rid1,source_id=cBA.source_id,target_id=cBA.target_id,similarity=0.1,conflict=0,pending=0,missed_alias_ids=[]));s.flush();raise SystemExit('唯一约束未生效')
 except Exception as ex:
  s.rollback();assert 'UNIQUE' in str(ex) or 'unique' in str(ex) or 'Integrity' in type(ex).__name__
 print('2) 重试幂等+唯一约束 ok')
 # --- 待补门牌对有分也禁止立案 ---
 try:
  proposal_service.create(s,{'code':'P-BAD','source_id':B.id,'target_id':A.id,'reason':'现场两位采集员核对门牌照片与地籍图，确认为同一入口'})
  raise SystemExit('待补门牌对不应允许立案')
 except HTTPException as e:
  assert e.status_code==409 and '待补' in e.detail
 print('3) 待补立案拦截 ok')
 # --- 补正与出分并发：补正抬升修订号，旧批次脱版，旧分旧待补不作数 ---
 entrance_service.alias_fix(s,bad_id,{'text':'长桥路十八号旧称'});s.commit()
 with Session() as s2:
  assert s2.get(Registry,1).revision==1
  assert s2.get(Alias,bad_id).state=='verified'
  # 旧批次仍 ready 但已与现行资料脱版：守卫查不到当前批次，放行（不拿旧待补当结果）
  run2=MatchRun(state='queued');s2.add(run2);s2.flush();rid2=run2.id
  process_run(s2,rid2);s2.commit()
  r1=s2.get(MatchRun,rid1);r2=s2.get(MatchRun,rid2)
  assert r1.state=='superseded' and r2.state=='ready' and r2.revision==1
  c2={(c.source_id,c.target_id):c for c in rows(s2,Candidate) if c.run_id==rid2}
  k=(A.id,B.id) if (A.id,B.id) in c2 else (B.id,A.id)
  assert c2[k].pending==0 and c2[k].missed_alias_ids==[]
  assert all(c.pending==0 for c in c2.values())
  assert r2.result['bad_aliases']==[]
  print('4) 补正重算+旧批脱版+待补清除 ok')
  # --- 补正后同街同号可立案；数字冲突仍拒 ---
  p=proposal_service.create(s2,{'code':'P-OK','source_id':B.id,'target_id':A.id,'reason':'现场两位采集员核对门牌照片与地籍图，确认为同一入口'});s2.commit()
  assert p.state=='draft'
  try:
   proposal_service.create(s2,{'code':'P-81','source_id':C.id,'target_id':A.id,'reason':'现场两位采集员核对门牌照片与地籍图，确认为同一入口'})
   raise SystemExit('数字冲突不应允许立案')
  except HTTPException as e:assert e.status_code==409
  # 补正成仍坏的文本被拒
  try:
   entrance_service.alias_fix(s2,bad_id,{'text':'长桥路十十号誊本'});raise SystemExit('坏文本补正应被拒')
  except HTTPException as e:assert e.status_code==409
  print('5) 补正后立案/冲突与坏文本校验 ok')
# --- register 聚合包含新字段 ---
from src.routes import router
from src.security import password_hash
from src.models import User
with Session() as s:
 u={'email':'supervisor@changqiao.local','role':'supervisor'}
 # 直接调用路由函数
 data=router.routes
 reg_fn=[r for r in router.routes if getattr(r,'path','')=='/register'][0].endpoint
 payload=reg_fn(u)
 assert 'candidates' in payload and all('pending' in c and 'missed_alias_ids' in c for c in payload['candidates'])
 assert payload['clock'][0]['revision']==1
 print('6) /register 新字段 ok')
print('ALL INTEGRATION TESTS PASSED')

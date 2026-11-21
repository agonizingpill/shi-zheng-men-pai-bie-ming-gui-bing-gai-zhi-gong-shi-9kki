import os,pathlib
TDIR=pathlib.Path('/tmp/addr-test');TDIR.mkdir(exist_ok=True)
os.environ['DATABASE_URL']='sqlite:///'+str(TDIR/'http.db')
os.environ['REDIS_URL']='redis://localhost:6399/0'
os.environ['JWT_SECRET']='test-secret'
os.environ['SEED_DEMO']='false'
import sys;sys.path.insert(0,'/workspace/backend')
if os.path.exists(TDIR/'http.db'):os.remove(TDIR/'http.db')
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src import database as db
db.engine=create_engine(os.environ['DATABASE_URL'])
db.Session=sessionmaker(db.engine,expire_on_commit=False)
from fastapi.testclient import TestClient
from src import routes
class FakeRedis:
 def rpush(self,k,v):queued.append(v)
 def ping(self):return True
queued=[]
routes.redis.from_url=lambda *a,**k:FakeRedis()
from src.main import app
from src.database import Session,engine,Base
from src.models import *
from src.common import rows
from src.worker import process_run
Base.metadata.create_all(engine)
from scripts.seed_demo import seed
seed()
def login(role):
 r=client.post('/auth/login',json={'email':f'{role}@changqiao.local','password':'Address2026!'})
 assert r.status_code==200,r.text
 return {'Authorization':'Bearer '+r.json()['token']}
with TestClient(app) as client:
 op=login('operator');sup=login('supervisor');vw=login('viewer')
 with Session() as s:
  bad=[a for a in rows(s,Alias) if '十十' in a.text][0];bid=bad.id
  ent={e.code:e for e in rows(s,Entrance)};A=ent['CQ-018-A'];B=ent['CQ-018-B']
 # viewer 只读：补正被拒
 r=client.patch(f'/aliases/{bid}',json={'text':'长桥路十八号旧称'},headers=vw)
 assert r.status_code==403,r.text
 # 坏文本补正被拒（operator）
 r=client.patch(f'/aliases/{bid}',json={'text':'长桥路十十号誊本'},headers=op)
 assert r.status_code==409 and '无法规范' in r.json()['detail']
 # 触发一次匹配（队列不可达时路由会把批次置 failed，故直接驱动 worker 处理 queued 批次）
 r=client.post('/matches',headers=op)
 if r.status_code==200:
  rid=r.json()['id']
  with Session() as s:process_run(s,rid);s.commit()
 reg=client.get('/register',headers=sup).json()
 run=[x for x in reg['runs'] if x['state']=='ready'][-1]
 pair=[c for c in reg['candidates'] if c['run_id']==run['id'] and {c['source_id'],c['target_id']}=={A.id,B.id}][0]
 assert pair['pending']==1 and bid in pair['missed_alias_ids'] and pair['similarity'] is not None
 assert reg['aliases']==[a for a in reg['aliases']]  # 结构完好
 assert any(a['id']==bid and a['state']=='pending_fix' for a in reg['aliases'])
 # 待补门牌对经 HTTP 立案被拒
 r=client.post('/proposals',json={'code':'P-HTTP-BAD','source_id':B.id,'target_id':A.id,'reason':'现场两位采集员核对门牌照片与地籍图，确认为同一入口'},headers=op)
 assert r.status_code==409 and '待补' in r.json()['detail']
 # operator 补正成功
 r=client.patch(f'/aliases/{bid}',json={'text':'长桥路十八号旧称'},headers=op)
 assert r.status_code==200 and r.json()['state']=='verified',r.text
 # 补正后重算
 r=client.post('/matches',headers=op);rid2=r.json()['id']
 with Session() as s:process_run(s,rid2);s.commit()
 reg=client.get('/register',headers=sup).json()
 cur=[x for x in reg['runs'] if x['id']==rid2][0]
 assert cur['state']=='ready' and cur['revision']==1
 assert [x['state'] for x in reg['runs'] if x['id']==run['id']]==['superseded']
 pair2=[c for c in reg['candidates'] if c['run_id']==rid2 and {c['source_id'],c['target_id']}=={A.id,B.id}][0]
 assert pair2['pending']==0 and pair2['missed_alias_ids']==[]
 # 现在可立案
 r=client.post('/proposals',json={'code':'P-HTTP-OK','source_id':B.id,'target_id':A.id,'reason':'现场两位采集员核对门牌照片与地籍图，确认为同一入口'},headers=op)
 assert r.status_code==200,r.text
 print('HTTP TESTS PASSED')

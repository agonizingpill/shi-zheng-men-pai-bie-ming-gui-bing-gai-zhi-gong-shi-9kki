import os,time,pathlib,logging
import redis
from sqlalchemy import select
from .database import Session
from .models import MatchRun,Entrance,Alias,Candidate,Registry
from .common import lock,rows,dump
from .matching import match,alias_quality
def process_run(s,run_id):
 lock(s);run=s.get(MatchRun,int(run_id))
 if not run or run.state!='queued':return
 try:
  revision=s.get(Registry,1).revision or 0
  entrances=[dump(x) for x in rows(s,Entrance)];alias_rows=rows(s,Alias);aliases=[dump(x) for x in alias_rows]
  # 坏别名留待补正：状态落库，整批匹配照常进行
  for x in alias_rows:
   ok,_=alias_quality(x.text)
   x.state='verified' if ok else 'pending_fix'
  result=match(entrances,aliases)
  run.result=result;run.revision=revision
  # 新批次出分后，旧批次（含旧分与旧待补状态）一律脱版，不能当作补正后的结果
  for old in s.scalars(select(MatchRun).where(MatchRun.state=='ready')).all():
   if old.id!=run.id:old.state='superseded'
  for d in result['pairs']:
   # 发布重试不重复出候选：同批次同门牌对只持久化一次
   exists=s.scalars(select(Candidate).where(Candidate.run_id==run.id,Candidate.source_id==d['source_id'],Candidate.target_id==d['target_id'])).first()
   if exists:continue
   s.add(Candidate(run_id=run.id,source_id=d['source_id'],target_id=d['target_id'],similarity=d['similarity'],conflict=d['conflict'],pending=d['pending'],missed_alias_ids=d['missed_alias_ids']))
  run.state='ready'
 except Exception as e:run.state='failed';run.error=str(e)[:500];logging.exception('matching failed')
def main():
 q=redis.from_url(os.environ['REDIS_URL'],decode_responses=True)
 while True:
  pathlib.Path('/artifacts/address-heartbeat').write_text(str(time.time()))
  item=q.blpop('address:matching',timeout=2)
  if not item:continue
  with Session() as s:
   process_run(s,item[1]);s.commit()
if __name__=='__main__':main()

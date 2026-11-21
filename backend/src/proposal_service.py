from .models import Entrance,Alias,Evidence,Proposal,Objection,Notice,MatchRun,Candidate,Registry
from .common import *
def pair(s,a,b):
 x=get(s,Entrance,a);y=get(s,Entrance,b)
 if a==b:fail('不能归并到自身')
 if x.street!=y.street or x.number!=y.number:fail('道路或门牌数字冲突，不得归并')
 return x,y
def guard_pending(s,a,b):
 # 仅以当前资料的最新已出分批次为准；旧分和旧待补状态（superseded）不得用于立案判断
 revision=(s.get(Registry,1).revision or 0)
 run=s.scalars(select(MatchRun).where(MatchRun.state=='ready',MatchRun.revision==revision).order_by(MatchRun.id.desc())).first()
 if not run:return
 c=s.scalars(select(Candidate).where(Candidate.run_id==run.id,((Candidate.source_id==a)&(Candidate.target_id==b))|((Candidate.source_id==b)&(Candidate.target_id==a)))).first()
 if c and c.pending:fail('该门牌对存在待补正坏别名，暂用分不得立案；请补正后重新计算')
def create(s,d):
 lock(s);pair(s,d['source_id'],d['target_id']);guard_pending(s,d['source_id'],d['target_id']);x=Proposal(**d);s.add(x);s.flush();return x
def object_to(s,d):
 lock(s);p=get(s,Proposal,d['proposal_id'])
 if p.state not in ['draft','public']:fail('只能在生效前提交异议')
 x=Objection(**d);s.add(x);s.flush();return x
def resolve(s,id,d):
 lock(s);x=get(s,Objection,id);p=get(s,Proposal,x.proposal_id)
 if x.state!='open' or p.state not in ['draft','public']:fail('异议已经处理或提案不可复核')
 x.state='resolved';x.decision=d['decision'];x.resolution=d['resolution']
 if x.decision=='split':
  p.state='rejected'
  for n in rows(s,Notice):
   if n.proposal_id==p.id:n.state='withdrawn'
 return x

from .models import Entrance,Alias,Evidence
from .constants import ALIAS_STATES
from .matching import alias_quality
from .common import *
def create_entrance(s,d):
 bump_revision(s);x=Entrance(**d);s.add(x);s.flush();return x
def locate(s,id,d):
 lock(s);x=get(s,Entrance,id);x.lat=d['lat'];x.lng=d['lng'];return x
def alias(s,d):
 bump_revision(s);get(s,Entrance,d['entrance_id']);x=Alias(**d);s.add(x);s.flush();return x
def alias_fix(s,id,d):
 bump_revision(s);x=get(s,Alias,id)
 if x.state not in ALIAS_STATES:fail('别名状态不允许补正')
 ok,bad_tokens=alias_quality(d['text'])
 if not ok:fail('补正文本仍含无法规范的门牌语 '+ '、'.join(bad_tokens)+'，请先改对')
 x.text=d['text'];x.state='verified';return x
def evidence(s,d):
 lock(s);get(s,Alias,d['alias_id']);x=Evidence(**d);s.add(x);s.flush();return x

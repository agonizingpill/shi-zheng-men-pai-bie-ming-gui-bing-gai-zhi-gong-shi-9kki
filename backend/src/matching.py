import re,hashlib,json
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import AgglomerativeClustering
from sklearn.metrics import precision_score,recall_score
from sklearn.model_selection import train_test_split
NUM={'零':0,'〇':0,'一':1,'二':2,'三':3,'四':4,'五':5,'六':6,'七':7,'八':8,'九':9}
TOKEN=re.compile(r'([0-9零〇一二三四五六七八九十]+)号')
def number(text):
 m=re.search(r'([0-9零〇一二三四五六七八九十]+)号',text)
 if not m:return None
 t=m.group(1)
 if t.isdigit():return int(t)
 if '十' in t:
  a,b=t.split('十');return (NUM.get(a,1) if a else 1)*10+(NUM.get(b,0) if b else 0)
 return int(''.join(str(NUM[x]) for x in t))
def parse_token(t):
 # 坏别名（如“十十号”“十十十号”）无法规范为门牌数字，返回None留给人工补正
 if t.isdigit():return int(t)
 if '十' in t:
  parts=t.split('十')
  if len(parts)!=2:return None
  a,b=parts
  if a and a not in NUM:return None
  if b and b not in NUM:return None
  if not a and b:return 10+NUM[b]
  tens=(NUM[a] if a else 1)*10;return tens+(NUM[b] if b else 0)
 if any(x not in NUM for x in t):return None
 return int(''.join(str(NUM[x]) for x in t))
def alias_quality(text):
 # 返回(是否可用, 坏词原文)；无“号”门牌语的别名不属于坏别名，只是不参与匹配
 bad=[]
 for m in TOKEN.finditer(text):
  if parse_token(m.group(1)) is None:bad.append(m.group(0))
 return (not bad),bad
def normalize(text):
 def repl(m):
  n=parse_token(m.group(1))
  return text[m.start():m.end()] if n is None else f'{n}号'
 return TOKEN.sub(repl,text)
# Simulated labelled historical alias pairs. Split before TFIDF fit/threshold selection.
def evaluation():
 pairs=[]
 for street in ['长桥路','青石街','河滨路','新民巷','榕树街','学府路','东湖路','西堤路','南苑街','北园街','柳岸路','梅花巷']:
  pairs.extend([(street+'18号',street+'十八号',1),(street+'18号南入口',street+'十八号南门',1),(street+'18号',street+'81号',0),(street+'18号',street+'19号',0)])
 tr,te=train_test_split(list(range(len(pairs))),test_size=.25,stratify=[x[2] for x in pairs],random_state=42)
 vec=TfidfVectorizer(analyzer='char',ngram_range=(1,3));vec.fit([normalize(t) for i in tr for t in pairs[i][:2]])
 def pred(ids,threshold):
  out=[]
  for i in ids:
   a,b,_=pairs[i];v=vec.transform([normalize(a),normalize(b)]);sim=float((v[0]@v[1].T).toarray()[0,0]);out.append(int(number(a)==number(b) and sim>=threshold))
  return out
 threshold=max([.35,.45,.55,.65,.75],key=lambda z:(precision_score([pairs[i][2] for i in tr],pred(tr,z),zero_division=0)+recall_score([pairs[i][2] for i in tr],pred(tr,z),zero_division=0),z))
 y=[pairs[i][2] for i in te];pr=pred(te,threshold)
 return {'seed':42,'train_pairs':len(tr),'holdout_pairs':len(te),'train_ids':tr,'holdout_ids':te,'precision':precision_score(y,pr,zero_division=0),'recall':recall_score(y,pr,zero_division=0),'threshold':threshold,'label_source':'模拟历史别名对；不代表真实地址精度'}
def match(entrances,aliases):
 if len(entrances)<2 or len(aliases)<2:raise ValueError('至少两个入口和两个有文字的别名')
 # 坏别名隔离：整批不再因一条坏别名报错，留待人工补正
 bad=[];good=[]
 for a in aliases:
  ok,bad_tokens=alias_quality(a['text'])
  if ok:good.append(a)
  else:bad.append({'alias_id':a['id'],'entrance_id':a['entrance_id'],'text':a['text'],'bad_tokens':bad_tokens})
 texts=[normalize(a['text']) for a in good]
 if len(good)>=2:
  vec=TfidfVectorizer(analyzer='char',ngram_range=(1,3));v=vec.fit_transform(texts);sim=(v@v.T).toarray();dist=np.clip(1-sim,0,2);np.fill_diagonal(dist,0)
  labels=AgglomerativeClustering(n_clusters=None,distance_threshold=.55,metric='precomputed',linkage='average').fit_predict(dist)
  clusters=[{'alias_id':a['id'],'label':int(k)} for a,k in zip(good,labels)]
 else:
  sim=np.zeros((len(good),len(good)));clusters=[]
 eval=evaluation();candidates=[];pairs=[]
 for i,x in enumerate(entrances):
  for y in entrances[i+1:]:
   ix=[j for j,a in enumerate(good) if a['entrance_id']==x['id']];iy=[j for j,a in enumerate(good) if a['entrance_id']==y['id']]
   x_bad={b['alias_id'] for b in bad if b['entrance_id']==x['id']};y_bad={b['alias_id'] for b in bad if b['entrance_id']==y['id']}
   # 门牌对只要漏比一条坏别名即待补：即使没出候选、已有暂用分也不得据此立案
   pending=bool(x_bad or y_bad);missed=sorted(x_bad|y_bad)
   if ix and iy:
    score=round(float(max(sim[a,b] for a in ix for b in iy)),6)
   else:
    score=None
   conflict=x['number']!=y['number'] or x['street']!=y['street']
   pairs.append({'source_id':x['id'],'target_id':y['id'],'similarity':score,'conflict':int(conflict),'pending':int(pending),'missed_alias_ids':missed})
   if score is not None and score>=.2:
    candidates.append({'source_id':x['id'],'target_id':y['id'],'similarity':score,'conflict':int(conflict),'pending':int(pending),'missed_alias_ids':missed})
 return {'algorithm':'字符TF-IDF+AgglomerativeClustering average linkage','source_sha256':hashlib.sha256(json.dumps([entrances,aliases],ensure_ascii=False,sort_keys=True).encode()).hexdigest(),'evaluation':eval,'bad_aliases':bad,'clusters':clusters,'pairs':pairs,'candidates':candidates}

#!/usr/bin/env python3
# Public-input-only native format converter. Requires PyYAML.
import yaml,json,hashlib,re,pathlib,collections
import argparse
a=argparse.ArgumentParser();a.add_argument('--mihomo-dir',required=True);a.add_argument('--geosite',required=True);a.add_argument('--output',required=True);args=a.parse_args()
R=pathlib.Path(args.mihomo_dir);OUT=pathlib.Path(args.output);OUT.mkdir(parents=True,exist_ok=True)
GEO=pathlib.Path(args.geosite)
def fields(b):
 i=0
 def vi():
  nonlocal i
  n=s=0
  while True:
   x=b[i];i+=1;n|=(x&127)<<s
   if x<128:return n
   s+=7
 while i<len(b):
  t=vi(); w=t&7
  if w==0:v=vi()
  elif w==2:n=vi();v=b[i:i+n];i+=n
  else:raise ValueError(w)
  yield t>>3,v
sites={}
for _,ent in fields(GEO.read_bytes()):
 fs=list(fields(ent));name=next(v.decode().lower() for k,v in fs if k==1); domains=[]
 for k,v in fs:
  if k==2:
   dd=dict(fields(v));domains.append((dd.get(1,0),dd[2].decode()))
 sites[name]=domains
mapping={'DOMAIN':'domain','DOMAIN-SUFFIX':'domain_suffix','DOMAIN-KEYWORD':'domain_keyword','DOMAIN-REGEX':'domain_regex','IP-CIDR':'ip_cidr','NETWORK':'protocol','DST-PORT':'dest_port'}
def rule(s):
 if s.startswith('AND,'):
  return {'and':{'match':[rule(v) for v in re.findall(r'\(([^()]+)\)',s)]}}
 p=s.split(','); typ=mapping[p[0]];val=p[1].lower() if typ=='protocol' else ','.join(p[1:]) if typ=='domain_regex' else p[1]
 return {typ:{'match':val}}
def add(d,r):
 k,v=next(iter(r.items()));d.setdefault(k+'_set',[]).append(v['match'])
def geos(d,name):
 for t,v in sites[name]:add(d,{{0:'domain_keyword',1:'domain_regex',2:'domain_suffix',3:'domain'}[t]:{'match':v}})
def write(name,d):
 for k,vs in d.items():
  seen=set(); d[k]=[v for v in vs if not (json.dumps(v,sort_keys=True) in seen or seen.add(json.dumps(v,sort_keys=True)))]
 (OUT/(name+'.yaml')).write_text('# MianRoute Egern native rule set; generated, no credentials.\n'+yaml.safe_dump(d,allow_unicode=True,sort_keys=False,width=150))
 return {k:len(v) for k,v in d.items()}
manifest={'geosite_sha256':hashlib.sha256(GEO.read_bytes()).hexdigest(),'geosite_source':'https://github.com/XTLS/Xray-rules-dat/releases/latest/download/geosite.dat','files':{}}
for name in ['apple-direct','apple-proxy','cn-direct','ads-exceptions']:
 d={}
 for s in yaml.safe_load((R/(name+'.yaml')).read_text())['payload']:
  if name=='apple-proxy' and s.startswith('AND,'):continue # use documented top-level AND in private profile
  add(d,rule(s))
 manifest['files'][name]=write(name,d)
d={}
for s in yaml.safe_load((R/'ads.yaml').read_text())['payload']:
 if s.startswith('+.'):typ,val='domain_suffix',s[2:]
 elif '*' in s:typ,val='domain_wildcard',s
 else:typ,val='domain',s
 add(d,{typ:{'match':val}})
manifest['files']['ads']=write('ads',d)
for name,tags in [('proxy-priority',['paypal','microsoft','ebay','linkedin','google']),('foreign-proxy',['steam','ubisoft','ea','playstation','nintendo','epicgames']),('foreign-general',['geolocation-!cn']),('cn-general',['cn']),('lan',['private'])]:
 d={}
 for tag in tags:geos(d,tag)
 if name=='proxy-priority':
  # Mainland sovereign Microsoft 365 endpoints (Microsoft 21Vianet, Common/Office Online ID 7).
  # https://learn.microsoft.com/en-us/microsoft-365/enterprise/urls-and-ip-address-ranges-21vianet?view=o365-worldwide#microsoft-365-common-and-office-online
  for s in ['paypal.cn','paypal.com.cn','microsoft.cn','azclient.cn','partner.microsoftonline-m-i.net.cn','partner.microsoftonline-m.net.cn','amazon.cn','z.cn','amazonbusiness.cn','amazonbusiness.com.cn','aboutamazon.cn']:add(d,{'domain_suffix':{'match':s}})
 if name=='lan':
  for s in ['127.0.0.0/8','10.0.0.0/8','172.16.0.0/12','192.168.0.0/16','169.254.0.0/16','100.64.0.0/10','224.0.0.0/4','255.255.255.255/32']:add(d,{'ip_cidr':{'match':s}})
 manifest['files'][name]=write(name,d)
(OUT.parent/'BUILD-MANIFEST.json').write_text(json.dumps(manifest,indent=2))
print(json.dumps(manifest['files'],indent=2))

#!/usr/bin/env python3
# Public-input-only native format converter. Requires PyYAML.
import yaml,json,hashlib,re,pathlib,collections
import argparse
a=argparse.ArgumentParser();a.add_argument('--mihomo-dir',required=True);a.add_argument('--geosite',required=True);a.add_argument('--output',required=True);a.add_argument('--geosite-source',help='URL of the exact GeoSite release used')
a.add_argument('--sync-cn-alias', action='store_true', help='Copy the canonical Mihomo cn-services provider to the legacy cn-direct path')
args=a.parse_args()
R=pathlib.Path(args.mihomo_dir);OUT=pathlib.Path(args.output);OUT.mkdir(parents=True,exist_ok=True)
GEO=pathlib.Path(args.geosite)
# The Mihomo subscription is the source of the enterprise ASN list. Its domain
# guard belongs only to Mihomo; Egern uses ASN matches later in cn-general.
cn_source = R / 'cn-services.yaml'
cn_alias = R / 'cn-direct.yaml'
if args.sync_cn_alias:
 cn_alias.write_bytes(cn_source.read_bytes())
if cn_alias.read_bytes() != cn_source.read_bytes():
 raise ValueError('Mihomo cn-direct and cn-services differ; compare them before syncing the legacy alias')
asn_rule = re.compile(r'AND,\(\(DOMAIN-REGEX,\^\$\),\(IP-ASN,([1-9][0-9]*),no-resolve\)\)')
service_asns = []
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
  if not isinstance(vs,list):continue
  seen=set(); d[k]=[v for v in vs if not (json.dumps(v,sort_keys=True) in seen or seen.add(json.dumps(v,sort_keys=True)))]
 if name in ('ads','ads-exceptions'):
  header = '# MianRoute public advertising rules. Generated from maintenance/ad-sources.lock.json.\n'
  body = yaml.dump(d, Dumper=yaml.CSafeDumper, allow_unicode=True, sort_keys=False, width=150)
 else:
  header = '# MianRoute Egern native rule set; generated, no credentials.\n'
  body = yaml.safe_dump(d, allow_unicode=True, sort_keys=False, width=150)
 (OUT/(name+'.yaml')).write_bytes((header+body).encode('utf-8'))
 return {k:len(v) for k,v in d.items() if isinstance(v,list)}
manifest_path = OUT.parent / 'BUILD-MANIFEST.json'
source_manifest = pathlib.Path(__file__).with_name('BUILD-MANIFEST.json')
previous_path = manifest_path if manifest_path.exists() else source_manifest
previous = json.loads(previous_path.read_text(encoding='utf-8')) if previous_path.exists() else {}
geosite_hash = hashlib.sha256(GEO.read_bytes()).hexdigest()
source = args.geosite_source or (previous.get('geosite_source') if previous.get('geosite_sha256') == geosite_hash else None)
manifest = {'geosite_sha256': geosite_hash, 'files': {}}
if source:
 manifest['geosite_source'] = source
for name in ['apple-direct','apple-proxy','cn-services','ads-exceptions']:
 d={}
 for s in yaml.safe_load((R/(name+'.yaml')).read_text(encoding='utf-8'))['payload']:
  if name in ('cn-services','cn-direct') and s.startswith('AND,'):
   match = asn_rule.fullmatch(s)
   if not match:
    raise ValueError('Unsupported mainland service rule: ' + s)
   if name=='cn-services':
    number = int(match.group(1))
    if number > 4294967295 or 'AS'+str(number) in service_asns:
     raise ValueError('Invalid or duplicated service ASN: ' + str(number))
    service_asns.append('AS'+str(number))
   continue
  if name=='apple-proxy' and s.startswith('AND,'):continue # use documented top-level AND in templates/egern.yaml
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
 if name=='cn-general' and service_asns:
  d['asn_set'] = service_asns
  d['no_resolve'] = True
 if name=='lan':
  for s in ['127.0.0.0/8','10.0.0.0/8','172.16.0.0/12','192.168.0.0/16','169.254.0.0/16','100.64.0.0/10','224.0.0.0/4','255.255.255.255/32']:add(d,{'ip_cidr':{'match':s}})
 manifest['files'][name]=write(name,d)
def hash_file(path):
 return hashlib.sha256(path.read_bytes()).hexdigest()
manifest['format'] = 'Egern native rule set'
manifest['validation'] = 'Static checks only, not Egern core/device validation'
manifest['apns_note'] = 'Six TCP/port/IP conditions are defined in templates/egern.yaml; apple-proxy.yaml contains the domain rules.'
source_names = ('ads', 'ads-custom', 'ads-exceptions', 'apple-direct', 'apple-proxy', 'cn-direct', 'cn-services', 'foreign-proxy')
manifest['source_files'] = {name+'.yaml': hash_file(R/(name+'.yaml')) for name in source_names if (R/(name+'.yaml')).is_file()}
manifest['output_sha256'] = {name+'.yaml': hash_file(OUT/(name+'.yaml')) for name in manifest['files']}
manifest_path.write_bytes((json.dumps(manifest, indent=2)+'\n').encode('utf-8'))
print(json.dumps(manifest['files'],indent=2))

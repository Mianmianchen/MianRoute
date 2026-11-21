# SPDX-License-Identifier: GPL-3.0-or-later
# Dependencies: Python 3 + PyYAML. Never include credentials in this directory.
from pathlib import Path
import json,yaml,csv,re,ipaddress,hashlib
B=Path(__file__).resolve().parent
A=B/'.ads-source-cache'; A.mkdir(exist_ok=True)
import urllib.request
manifest=json.loads((B/'ADS-MANIFEST.json').read_text())
for name,src in zip(['hagezi.txt','adguard.txt'],manifest['sources']):
 target=A/name
 if not target.exists(): target.write_bytes(urllib.request.urlopen(src['url']).read())
 if hashlib.sha256(target.read_bytes()).hexdigest()!=src['sha256']:
  raise SystemExit('Upstream changed: review the new snapshot and update manifest before building.')
base={s.strip().lower() for s in (A/'hagezi.txt').read_text().splitlines() if s.strip() and not s.startswith('#')}
ad=set();ex=[];ignored=[];ips=[];other=[]
for s in (A/'adguard.txt').read_text().splitlines():
 if not s or s.startswith(('!','#')):continue
 m=re.fullmatch(r'\|\|([a-zA-Z0-9_.-]+)\^',s)
 if m:
  d=m[1].lower()
  try:ipaddress.ip_address(d);ips.append(s)
  except ValueError:ad.add(d)
 elif s.startswith('@@'):
  m=re.fullmatch(r'@@(\|\||\|)?([a-zA-Z0-9_.*-]+)\^\|?',s)
  if not m:
   ignored.append(s);continue
  anchor,pat=m.groups();pat=pat.lower()
  if anchor=='||' and '*' not in pat:typ='DOMAIN-SUFFIX';v=pat;rg='(?:^|\\.)'+re.escape(pat)+'$'
  elif anchor=='|' and '*' not in pat:typ='DOMAIN';v=pat;rg='^'+re.escape(pat)+'$'
  else:
   typ='DOMAIN-REGEX';rg=('(?:^|\\.)' if anchor=='||' else '^' if anchor=='|' else '')+re.escape(pat).replace(r'\*','.*')+'$';v=rg
  ex.append(dict(original=s,type=typ,value=v,regex=rg))
 else:other.append(s)
custom={'adukwai.com','adkwai.com','open.e.kuaishou.cn','open.e.kuaishou.com','open.kuaishouzt.com','open.kwaizt.com'}
all_domains=base|ad|custom
# Apply individually approved fixes to the union, never mutate source snapshots.
for correction in manifest.get('reviewed_removals', []):
 d=correction['domain']
 if d not in all_domains:
  raise SystemExit('Review removal no longer matches a pinned input: '+d)
 all_domains.remove(d)
def parents(d):
 t=d.split('.');return ['.'.join(t[i:]) for i in range(len(t)-1)]
minimal={d for d in all_domains if not any(a in all_domains for a in parents(d)[1:])}
for d in all_domains:assert any(a in minimal for a in parents(d))
(B/'ads.yaml').write_text('# HaGeZi PRO + AdGuard DNS unconditional domain rules + verified Kuaishou domains.\n# Must be used with ads-exceptions.yaml using AND / NOT; see ADS-SOURCES.md.\n# Fixed-source snapshot, GPL-3.0 source notices in ADS-SOURCES.md and ADS-LICENSE-GPL-3.0.txt.\n'+yaml.safe_dump({'payload':['+.'+d for d in sorted(minimal)]},sort_keys=False))
(B/'ads-exceptions.yaml').write_text('# AdGuard DNS domain exceptions; bypass advertising rule only, not force DIRECT.\n'+yaml.safe_dump({'payload':[e['type']+','+e['value'] for e in ex]},sort_keys=False))

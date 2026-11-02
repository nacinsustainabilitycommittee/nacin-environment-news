#!/usr/bin/env python3
"""Collect metadata from open news discovery APIs. Never scrape or republish articles."""
import datetime as dt, hashlib, json, os, pathlib, re, time, urllib.parse, urllib.request
from urllib.error import URLError, HTTPError

ROOT=pathlib.Path(__file__).resolve().parents[1]
DATA=ROOT/'site'/'data'
QUERIES=['"wildlife trafficking"', '"wildlife smuggling"', '"illegal wildlife trade"', '"pangolin" "seized"', '"ivory" "seized"', '"exotic animals" "smuggling"', '"tortoises" "smuggled"']
KEYWORDS=('wildlife','traffick','smuggl','seiz','pangolin','ivory','rhino','tortoise','turtle','reptile','exotic animal','protected species','elephant','parrot','gecko','endangered','cites','poach')
ACTION=('traffick','smuggl','seiz','arrest','confiscat','illegal','intercept','poach','bust','rescued','trade','shipment')
MAX_ITEMS=400

def read_json(path, default):
    try: return json.loads(path.read_text(encoding='utf-8'))
    except (FileNotFoundError, ValueError): return default

def write_json(path, val):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix('.tmp')
    tmp.write_text(json.dumps(val,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    tmp.replace(path)

def normalize_url(url):
    parts=urllib.parse.urlsplit(url.strip())
    if parts.scheme not in ('https','http') or not parts.netloc: return None
    params=urllib.parse.parse_qsl(parts.query,keep_blank_values=True)
    params=[(k,v) for k,v in params if not (k.lower().startswith('utm_') or k.lower() in ('fbclid','gclid'))]
    return urllib.parse.urlunsplit((parts.scheme,parts.netloc.lower(),parts.path.rstrip('/') or '/',urllib.parse.urlencode(params),'')).strip()

def relevant(title):
    t=title.lower()
    return any(k in t for k in KEYWORDS) and any(k in t for k in ACTION)

def fetch(query):
    params=urllib.parse.urlencode({'query':query,'mode':'ArtList','format':'json','sort':'DateDesc','maxrecords':75,'timespan':'3d'})
    req=urllib.request.Request('https://api.gdeltproject.org/api/v2/doc/doc?'+params,headers={'User-Agent':'NACIN-Environment-News/1.0 (educational open-source metadata aggregator)','Accept':'application/json'})
    with urllib.request.urlopen(req,timeout=30) as resp:
        return json.load(resp).get('articles',[])

def collect():
    now=dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')
    pending=read_json(DATA/'pending.json',[])
    published=read_json(DATA/'published.json',[])
    rejected=read_json(DATA/'rejected.json',[])
    known={a['id'] for a in pending+published+rejected}
    found=0; failures=[]
    for query in QUERIES:
        try: articles=fetch(query)
        except (URLError,HTTPError,TimeoutError,ValueError, OSError) as exc:
            failures.append({'query':query,'error':str(exc)[:200]}); continue
        for a in articles:
            title=re.sub(r'\s+',' ',a.get('title','')).strip()[:240]
            url=normalize_url(a.get('url',''))
            if not url or not relevant(title): continue
            id_=hashlib.sha256(url.encode()).hexdigest()[:16]
            if id_ in known: continue
            seen=a.get('seendate','')
            try: stamp=dt.datetime.strptime(seen,'%Y%m%dT%H%M%SZ').replace(tzinfo=dt.timezone.utc).isoformat()
            except ValueError: stamp=None
            pending.append({'id':id_,'title':title,'url':url,'source':a.get('domain') or urllib.parse.urlsplit(url).netloc,'source_country':a.get('sourcecountry') or None,'published_at':stamp,'discovered_at':now,'status':'pending','query':query,'editor_note':'','category':'Wildlife trafficking'})
            known.add(id_); found+=1
        time.sleep(1)
    pending=sorted(pending,key=lambda a:a['discovered_at'],reverse=True)[:MAX_ITEMS]
    write_json(DATA/'pending.json',pending)
    write_json(DATA/'last_run.json',{'collected_at':now,'new_candidates':found,'pending_total':len(pending),'query_failures':failures})
    print(f'New: {found}; pending: {len(pending)}; failed searches: {len(failures)}')
    for failure in failures:
    print(f"Search failed: {failure['query']} — {failure['error']}")
    if len(failures)==len(QUERIES): raise SystemExit('All news sources failed; check connectivity/rate limits')

if __name__=='__main__': collect()

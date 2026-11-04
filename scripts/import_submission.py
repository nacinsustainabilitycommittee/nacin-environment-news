#!/usr/bin/env python3
"""Import a GitHub Issue Form submission as an unapproved news candidate.

Never run issue body as shell/code. The workflow fetches public issue fields as JSON.
"""
import argparse, datetime as dt, hashlib, json, pathlib, re, urllib.parse
from collector import DATA, read_json, write_json, normalize_url

INCIDENT_TYPES={'Unknown','Seizure','Smuggling','Trafficking','Poaching','Arrest / Investigation','Other'}

CATEGORIES = {'Wildlife trafficking','Wildlife conservation','Seizures & enforcement','CITES & wildlife law','Research & reports'}

def section(body, label):
    m = re.search(r'^### ' + re.escape(label) + r'\s*\n(.*?)(?=^### |\Z)',body,re.M|re.S)
    return m.group(1).strip() if m else ''

def import_issue(issue):
    if 'news-submission' not in [x['name'] if isinstance(x,dict) else x for x in issue.get('labels',[])]:
        raise ValueError('Issue is not labeled news-submission')
    body=issue.get('body') or ''
    title=section(body,'Article headline')[:240]
    url=normalize_url(section(body,'Original article URL'))
    category=section(body,'Category')
    if not title or title in ('_No response_','No response'): raise ValueError('Missing article headline')
    if not url: raise ValueError('Invalid public HTTP(S) article URL')
    if category not in CATEGORIES: raise ValueError('Unknown category')
    id_=hashlib.sha256(url.encode('utf-8')).hexdigest()[:16]
    paths=[DATA/f'{s}.json' for s in ('pending','published','rejected')]
    if any(any(x.get('id')==id_ for x in read_json(path,[])) for path in paths):
        print('Already indexed: '+id_);return False
    raw_date=section(body,'Article publication date')
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', raw_date):
        raise ValueError('Article publication date is required in YYYY-MM-DD format')
    try:
        article_date=dt.date.fromisoformat(raw_date)
    except ValueError as exc:
        raise ValueError('Invalid article publication date') from exc
    if article_date > dt.datetime.now(dt.timezone.utc).date():
        raise ValueError('Article publication date cannot be in the future')
    published_at=article_date.isoformat()
    raw_species=section(body,'Species or wildlife product (optional)')
    species=[x.strip()[:90] for x in raw_species.split(',') if x.strip() and x.strip() not in ('_No response_','No response')][:12]
    raw_country=section(body,'Incident country (optional)')
    country=raw_country.strip()[:100] if raw_country and raw_country not in ('_No response_','No response') else None
    raw_type=section(body,'Incident type (optional)')
    incident_type=raw_type if raw_type in INCIDENT_TYPES and raw_type!='Unknown' else None
    now=dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')
    submitter=issue.get('author',{}).get('login','unknown')
    number=issue.get('number')
    record={'id':id_,'title':title,'url':url,'source':urllib.parse.urlsplit(url).netloc,
        'source_country':None,'published_at':published_at,'discovered_at':now,'status':'pending',
        'query':None,'editor_note':'','category':category,'submission_type':'manual',
        'submitted_by':submitter,'github_issue':number,
        'species':species,'incident_country':country,'incident_type':incident_type,
        'metadata_status':'unverified',
        'submission_note':section(body,'Relevance to Customs officers (optional)')[:1000]}
    pending=read_json(DATA/'pending.json',[])
    pending.insert(0,record)
    write_json(DATA/'pending.json',pending)
    print('Imported as pending: '+id_)
    return True

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('json_file',type=pathlib.Path)
    args=parser.parse_args()
    import_issue(json.loads(args.json_file.read_text(encoding='utf-8')))

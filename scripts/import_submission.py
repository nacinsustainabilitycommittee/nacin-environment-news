#!/usr/bin/env python3
"""Import a GitHub Issue Form submission as an unapproved news candidate.

Never run issue body as shell/code. The workflow fetches public issue fields as JSON.
"""
import argparse, datetime as dt, hashlib, json, pathlib, re, urllib.parse
from collector import DATA, read_json, write_json, normalize_url

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
    now=dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')
    submitter=issue.get('author',{}).get('login','unknown')
    number=issue.get('number')
    record={'id':id_,'title':title,'url':url,'source':urllib.parse.urlsplit(url).netloc,
        'source_country':None,'published_at':None,'discovered_at':now,'status':'pending',
        'query':None,'editor_note':'','category':category,'submission_type':'manual',
        'submitted_by':submitter,'github_issue':number,
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

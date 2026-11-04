#!/usr/bin/env python3
"""Editorial decision utility: requires trusted repository write access."""
import argparse,datetime as dt,json,pathlib
from collector import DATA,read_json,write_json

def review(story_id,decision,editor,note,species=None,country=None,verification="unverified", publication_date=None):
    if not editor.strip(): raise ValueError('Editor name is required')
    pending=read_json(DATA/'pending.json',[])
    target=next((x for x in pending if x['id']==story_id),None)
    if target is None: raise ValueError('Story ID not present in pending queue')
    if species:
        target['species']=[s.strip()[:90] for s in species.split(',') if s.strip()][:12]
    if country:
        target['incident_country']=country.strip()[:100] or None
    if publication_date:
        try:
            clean=dt.date.fromisoformat(publication_date).isoformat()
            if clean != publication_date or dt.date.fromisoformat(clean) > dt.datetime.now(dt.timezone.utc).date():
                raise ValueError('Invalid or future publication date')
        except ValueError as exc:
            raise ValueError('Publication date must be real YYYY-MM-DD, not in future') from exc
        target['published_at']=clean
    if verification not in ('verified','unknown','unverified'):
        raise ValueError('Invalid verification status')
    # Only explicitly editor-verified records qualify for incident-level charts.
    if verification=='verified':
        if not target.get('species') or not target.get('incident_country') or target.get('incident_country','').lower() in ('unknown','not specified'):
            raise ValueError('Verified metadata requires species and incident country')
    target['metadata_status']=verification
    pending=[x for x in pending if x['id']!=story_id]
    target['status']='published' if decision=='approve' else 'rejected'
    target['editor_note']=note[:1000]
    target['reviewed_at']=dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')
    target['reviewed_by']=editor
    dest='published.json' if decision=='approve' else 'rejected.json'
    items=read_json(DATA/dest,[])
    items.insert(0,target)
    write_json(DATA/'pending.json',pending)
    write_json(DATA/dest,items)
    audit=read_json(DATA/'audit.json',[])
    audit.insert(0,{'id':story_id,'decision':decision,'editor':editor,'note':note[:1000],'at':target['reviewed_at']})
    write_json(DATA/'audit.json',audit)
    print(f'{decision}: {story_id}')

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('id');p.add_argument('decision',choices=['approve','reject']);p.add_argument('--editor',required=True);p.add_argument('--note',default='')
    p.add_argument('--species',default=None,help='Comma-separated verified species/product names')
    p.add_argument('--country',default=None,help='Incident country, NOT news outlet country')
    p.add_argument('--publication-date',default=None,help='Editor-confirmed article publication date YYYY-MM-DD')
    p.add_argument('--verification',choices=['verified','unknown','unverified'],default='unverified')
    args=p.parse_args();review(args.id,args.decision,args.editor,args.note,args.species,args.country,args.verification,args.publication_date)

#!/usr/bin/env python3
"""Editorial decision utility: requires trusted repository write access."""
import argparse,datetime as dt,json,pathlib
from collector import DATA,read_json,write_json

def review(story_id,decision,editor,note):
    if not editor.strip(): raise ValueError('Editor name is required')
    pending=read_json(DATA/'pending.json',[])
    target=next((x for x in pending if x['id']==story_id),None)
    if target is None: raise ValueError('Story ID not present in pending queue')
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
    args=p.parse_args();review(args.id,args.decision,args.editor,args.note)

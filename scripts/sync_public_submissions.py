#!/usr/bin/env python3
"""Import public Supabase submissions into NACIN's editorial review queue.

This imports structured metadata without approving articles. It expects the public
submission form to store publication_date, species and incident_country in Supabase.
"""
import hashlib
import json
import os
import pathlib
import sys
import urllib.parse
import urllib.request
from datetime import date, datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / 'site' / 'data'
BATCH = ROOT / '.submission-sync-batch.json'
BASE = os.environ['SUPABASE_URL'].rstrip('/')
KEY = os.environ['SUPABASE_SECRET_KEY']


def api(method, path, payload=None):
    body = json.dumps(payload).encode('utf-8') if payload is not None else None
    headers = {
        'apikey': KEY,
        'Content-Type': 'application/json',
        'Prefer': 'return=minimal',
        'User-Agent': 'NACIN-News-Importer/1.1',
    }
    if not KEY.startswith('sb_secret_'):
        headers['Authorization'] = 'Bearer ' + KEY
    req = urllib.request.Request(BASE + '/rest/v1/' + path, data=body, method=method, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as r:
        response = r.read()
        return json.loads(response) if response else None


def read(name):
    path = DATA / name
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else []


def write(name, value):
    path = DATA / name
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temp.replace(path)


def normalize_url(url):
    parts = urllib.parse.urlsplit(str(url or '').strip())
    if parts.scheme not in ('http', 'https') or not parts.hostname:
        return None
    params = urllib.parse.parse_qsl(parts.query, keep_blank_values=True)
    params = [(k, v) for k, v in params if not (k.lower().startswith('utm_') or k.lower() in ('fbclid', 'gclid'))]
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc.lower(), parts.path.rstrip('/') or '/', urllib.parse.urlencode(params), ''))


def valid_publication_date(value):
    if not isinstance(value, str) or not value.strip():
        return None
    raw = value.strip()
    try:
        parsed = date.fromisoformat(raw)
    except ValueError:
        return None
    if parsed.isoformat() != raw or parsed > datetime.now(timezone.utc).date():
        return None
    return raw


def normalize_species(value):
    if isinstance(value, list):
        return [str(s).strip() for s in value if str(s).strip()]
    return [part.strip() for part in str(value or '').split(',') if part.strip()]


def pull():
    pending = read('pending.json')
    existing = {a['id'] for a in pending + read('published.json') + read('rejected.json')}
    # Select * preserves compatibility with databases before the optional columns
    # are added; new fields are included automatically once present.
    rows = api('GET', 'news_submissions?status=eq.pending&select=*&order=id.asc&limit=100') or []
    imported_ids = []
    added = 0
    skipped = 0
    for row in rows:
        url = normalize_url(row.get('url'))
        title = str(row.get('title') or '').strip()
        published_at = valid_publication_date(row.get('publication_date'))
        if not url or not title or not published_at:
            skipped += 1
            print(f"Skipping submission {row.get('id')}: title, valid URL, or YYYY-MM-DD publication date missing/invalid")
            continue
        article_id = hashlib.sha256(url.encode()).hexdigest()[:16]
        if article_id in existing:
            # Already reviewed or queued; safely acknowledge it rather than reimporting.
            imported_ids.append(row['id'])
            continue
        source = urllib.parse.urlsplit(url).hostname
        pending.append({
            'id': article_id,
            'title': title[:240],
            'url': url,
            'source': source,
            'source_country': None,  # Never infer publisher location from incident country
            'published_at': published_at,
            'discovered_at': row.get('created_at') or datetime.now(timezone.utc).isoformat(),
            'status': 'pending',
            'query': 'Public submission',
            'editor_note': row.get('description') or '',
            'category': row.get('category') or 'Wildlife trafficking',
            'origin': 'Public submission',
            'species': normalize_species(row.get('species')),
            'incident_country': str(row.get('incident_country') or '').strip() or None,
            'incident_state': (str(row.get('incident_state') or '').strip() or None
    if str(row.get('incident_country') or '').strip().lower() == 'india'
    else None
),

            'metadata_status': 'unverified',
        })
        existing.add(article_id)
        imported_ids.append(row['id'])
        added += 1
    pending.sort(key=lambda a: a.get('discovered_at') or '', reverse=True)
    write('pending.json', pending)
    BATCH.write_text(json.dumps(imported_ids), encoding='utf-8')
    print(f'New pending articles: {added}; duplicate acknowledgements: {len(imported_ids) - added}; invalid submissions left pending: {skipped}')


def mark():
    ids = json.loads(BATCH.read_text(encoding='utf-8'))
    now = datetime.now(timezone.utc).isoformat()
    for id_ in ids:
        encoded = urllib.parse.quote(str(id_), safe='')
        api('PATCH', 'news_submissions?id=eq.' + encoded, {'status': 'imported', 'imported_at': now})
    print(f'Marked {len(ids)} submissions imported')


if __name__ == '__main__':
    if len(sys.argv) != 2 or sys.argv[1] not in ('pull', 'mark'):
        raise SystemExit('Usage: sync_public_submissions.py pull|mark')
    {'pull': pull, 'mark': mark}[sys.argv[1]]()

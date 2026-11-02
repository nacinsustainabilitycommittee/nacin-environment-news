#!/usr/bin/env python3
"""Discover wildlife-trafficking news metadata for human editorial review.

Uses a small number of GDELT searches and Google News RSS as a fallback.
Never downloads or republishes article bodies.
"""
import datetime as dt
import email.utils
import hashlib
import json
import pathlib
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from urllib.error import HTTPError, URLError

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / 'site' / 'data'
GDELT_QUERIES = ['"wildlife trafficking" OR "wildlife smuggling"', '"illegal wildlife trade" OR "pangolin seizure"']
RSS_QUERIES = ['wildlife trafficking OR wildlife smuggling', 'pangolin OR ivory OR tortoise smuggling', 'illegal wildlife trade seizure']
KEYWORDS = ('wildlife','traffick','smuggl','seiz','pangolin','ivory','rhino','tortoise','turtle','reptile','exotic animal','protected species','elephant','parrot','gecko','endangered','cites','poach')
ACTION = ('traffick','smuggl','seiz','arrest','confiscat','illegal','intercept','poach','bust','rescued','trade','shipment')
MAX_ITEMS = 400
HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; NACIN-Environment-News/1.1; news metadata reader)', 'Accept': 'application/json, application/rss+xml, application/xml;q=0.9'}


def read_json(path, default):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (FileNotFoundError, ValueError):
        return default


def write_json(path, val):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(val, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    tmp.replace(path)


def normalize_url(url):
    if not isinstance(url, str):
        return None
    parts = urllib.parse.urlsplit(url.strip())
    if parts.scheme not in ('https', 'http') or not parts.netloc:
        return None
    params = urllib.parse.parse_qsl(parts.query, keep_blank_values=True)
    params = [(k,v) for k,v in params if not (k.lower().startswith('utm_') or k.lower() in ('fbclid','gclid'))]
    return urllib.parse.urlunsplit((parts.scheme,parts.netloc.lower(),parts.path.rstrip('/') or '/',urllib.parse.urlencode(params),'')).strip()


def relevant(title):
    t = title.lower()
    return any(k in t for k in KEYWORDS) and any(k in t for k in ACTION)


def request_bytes(url, accept='application/json', retries=1):
    headers = dict(HEADERS, Accept=accept)
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=25) as resp:
                return resp.read(2_000_000)
        except HTTPError as exc:
            if exc.code != 429 or attempt >= retries:
                raise
            retry_after = exc.headers.get('Retry-After', '10')
            try:
                delay = min(20, max(3, int(retry_after)))
            except ValueError:
                delay = 10
            print(f'HTTP 429 received; waiting {delay}s before retry', flush=True)
            time.sleep(delay)


def fetch_gdelt(query):
    params = urllib.parse.urlencode({'query':query,'mode':'ArtList','format':'json','sort':'DateDesc','maxrecords':50,'timespan':'3d'})
    url = 'https://api.gdeltproject.org/api/v2/doc/doc?' + params
    payload = json.loads(request_bytes(url, 'application/json').decode('utf-8-sig'))
    if not isinstance(payload, dict):
        raise ValueError('Unexpected GDELT response')
    return [dict(item, origin='GDELT') for item in payload.get('articles', [])]


def fetch_google_rss(query):
    params = urllib.parse.urlencode({'q': query + ' when:3d', 'hl':'en', 'gl':'US', 'ceid':'US:en'})
    url = 'https://news.google.com/rss/search?' + params
    root = ET.fromstring(request_bytes(url, 'application/rss+xml, application/xml'))
    if root.tag != 'rss':
        raise ValueError('Unexpected RSS document')
    articles = []
    for item in root.findall('./channel/item')[:50]:
        source = item.find('source')
        title = (item.findtext('title') or '').strip()
        link = (item.findtext('link') or '').strip()

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
        published_at = None
        pub_date = item.findtext('pubDate')
        if pub_date:
            try:
                published_at = email.utils.parsedate_to_datetime(pub_date).astimezone(dt.timezone.utc).isoformat()
            except (TypeError, ValueError, OverflowError):
                pass
        articles.append({'title': title, 'url': link,
                         'domain': (source.text or '').strip() if source is not None else 'Google News RSS',
                         'sourcecountry': None, 'published_at': published_at, 'origin':'Google News RSS'})
    return articles


def collect():
    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')
    pending = read_json(DATA/'pending.json', [])
    published = read_json(DATA/'published.json', [])
    rejected = read_json(DATA/'rejected.json', [])
    known = {a['id'] for a in pending + published + rejected if 'id' in a}
    found, failures, successful_searches = 0, [], 0
    source_counts = {'GDELT': 0, 'Google News RSS': 0}

    # Two API requests maximum, with spacing to reduce 429 responses.
    sources = [(q, fetch_gdelt) for q in GDELT_QUERIES]
    for i, (query, fetcher) in enumerate(sources):
        if i:
            time.sleep(4)
        try:
            articles = fetcher(query)
            successful_searches += 1
        except (HTTPError, URLError, TimeoutError, ValueError, OSError, ET.ParseError) as exc:
            failures.append({'query':query,'source':'GDELT','error':str(exc)[:200]})
            print(f'GDELT search failed: {query}: {exc}', flush=True)
            # 429 indicates API-wide rate limits; don't make another GDELT request.
            if isinstance(exc, HTTPError) and exc.code == 429:
                break
            continue
        found += add_articles(articles, query, now, pending, known, source_counts)

    # Supplement GDELT when available, and provide fallback if it is rate-limited.
    for query in RSS_QUERIES:
        try:
            articles = fetch_google_rss(query)
            successful_searches += 1
        except (HTTPError, URLError, TimeoutError, ValueError, OSError, ET.ParseError) as exc:
            failures.append({'query':query,'source':'Google News RSS','error':str(exc)[:200]})
            print(f'RSS search failed: {query}: {exc}', flush=True)
            continue
        found += add_articles(articles, query, now, pending, known, source_counts)
        time.sleep(1)

    pending = sorted(pending, key=lambda a: a.get('discovered_at') or '', reverse=True)[:MAX_ITEMS]
    write_json(DATA/'pending.json', pending)
    write_json(DATA/'last_run.json', {
        'collected_at':now, 'new_candidates':found, 'pending_total':len(pending),
        'successful_searches':successful_searches, 'query_failures':failures,
        'new_by_source':source_counts
    })
    print(f'New: {found}; pending: {len(pending)}; successful searches: {successful_searches}; failed searches: {len(failures)}', flush=True)
    if successful_searches == 0:
        raise SystemExit('All news sources failed; check connectivity, rate limits, or RSS availability')


def add_articles(articles, query, now, pending, known, counts):
    added = 0
    for a in articles:
        title = re.sub(r'\s+', ' ', a.get('title') or '').strip()[:240]
        url = normalize_url(a.get('url') or '')
        if not url or not relevant(title):
            continue
        id_ = hashlib.sha256(url.encode()).hexdigest()[:16]
        if id_ in known:
            continue
        stamp = a.get('published_at')
        if stamp is None and a.get('seendate'):
            try:
                stamp = dt.datetime.strptime(a['seendate'],'%Y%m%dT%H%M%SZ').replace(tzinfo=dt.timezone.utc).isoformat()
            except ValueError:
                pass
        origin = a.get('origin', 'GDELT')
        pending.append({
            'id':id_, 'title':title, 'url':url,
            'source':a.get('domain') or urllib.parse.urlsplit(url).netloc,
            'source_country':a.get('sourcecountry') or None,
            'published_at':stamp, 'discovered_at':now, 'status':'pending',
            'query':query, 'editor_note':'', 'category':'Wildlife trafficking'
        })
        known.add(id_)
        counts[origin] = counts.get(origin, 0) + 1
        added += 1
    return added


if __name__ == '__main__':
    collect()


import os
import sys
import json
import hashlib
import pathlib
import urllib.request
import urllib.parse
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "site" / "data"
BATCH = ROOT / ".submission-sync-batch.json"

BASE = os.environ["SUPABASE_URL"].rstrip("/")
KEY = os.environ["SUPABASE_SECRET_KEY"]

def api(method, path, payload=None):
    body = (
        json.dumps(payload).encode("utf-8")
        if payload is not None else None
    )
    req = urllib.request.Request(
        BASE + "/rest/v1/" + path,
        data=body,
        method=method,
        headers={
            "apikey": KEY,
            "Authorization": "Bearer " + KEY,
            "Content-Type": "application/json",
            "Prefer": "return=minimal"
        }
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read() or b"null")

def read(name):
    path = DATA / name
    return json.loads(path.read_text()) if path.exists() else []

def write(name, value):
    (DATA / name).write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8"
    )

def pull():
    pending = read("pending.json")
    existing = {
        a["id"] for a in (
            pending + read("published.json") +
            read("rejected.json")
        )
    }

    rows = api(
        "GET",
        "news_submissions?status=eq.pending"
        "&select=id,title,url,description,created_at"
        "&order=id.asc&limit=100"
    )

    ids = []

    for row in rows:
        ids.append(row["id"])
        url = row["url"].strip()
        parts = urllib.parse.urlsplit(url)

        if parts.scheme not in ("http", "https"):
            continue
        if not parts.hostname:
            continue

        params = urllib.parse.parse_qsl(
            parts.query, keep_blank_values=True
        )
        params = [
            (k, v) for k, v in params
            if not (k.lower().startswith("utm_")
                    or k.lower() in ("fbclid", "gclid"))
        ]
        normalized = urllib.parse.urlunsplit((
            parts.scheme, parts.netloc.lower(),
            parts.path.rstrip("/") or "/",
            urllib.parse.urlencode(params), ""
        ))

        article_id = hashlib.sha256(
            normalized.encode()
        ).hexdigest()[:16]

        if article_id in existing:
            continue

        pending.append({
            "id": article_id,
            "title": row["title"],
            "url": normalized,
            "source": parts.hostname,
            "source_country": None,
            "published_at": None,
            "discovered_at": row["created_at"],
            "status": "pending",
            "query": "Public submission",
            "editor_note": row.get("description") or "",
            "category": "Wildlife trafficking",
            "origin": "Public submission"
        })
        existing.add(article_id)

    pending.sort(
        key=lambda a: a.get("discovered_at") or "",
        reverse=True
    )
    write("pending.json", pending)
    BATCH.write_text(json.dumps(ids))
    print(f"Processed {len(ids)} public submissions")

def mark():
    ids = json.loads(BATCH.read_text())
    now = datetime.now(timezone.utc).isoformat()
    for id_ in ids:
        api(
            "PATCH",
            "news_submissions?id=eq." + str(id_),
            {"status": "imported", "imported_at": now}
        )
    print(f"Marked {len(ids)} as imported")

if __name__ == "__main__":
    if sys.argv[1] == "pull":
        pull()
    elif sys.argv[1] == "mark":
        mark()

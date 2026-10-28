"""Daily metrics snapshot for Two Words Kids, written to metrics/YYYY-MM-DD.json and metrics/latest.json.
Instagram: followers + per-post views/reach/likes/saves for every post in instagram/posted.json (IG_ACCESS_TOKEN, IG_USER_ID).
Etsy: shop sales count + per-listing views/favorites from the public Open API v3 (ETSY_API_KEY = "keystring:shared_secret").
Each source is skipped when its secret is missing or its API fails, so one broken source never blocks the others.
Run: python3 scripts/metrics.py"""
import json, os, datetime, urllib.request, urllib.parse, urllib.error
IG = "https://graph.instagram.com/v21.0"
ETSY = "https://openapi.etsy.com/v3/application"
SHOP = "TwoWordsKids"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def get(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=60) as r: return json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:400]; print("HTTP", e.code, url.split("?")[0], body); return {"error": body}
    except urllib.error.URLError as e:
        print("network error", url.split("?")[0], e.reason); return {"error": str(e.reason)}
def insights(media_id, kind, tok):
    # Reels and feed images support different metric sets; ask for the full set, then fall back to reach only
    full = "views,reach,likes,comments,saved,shares,total_interactions" if kind == "reel" else "views,reach,likes,comments,saved,shares"
    for metrics in (full, "reach"):
        r = get(f"{IG}/{media_id}/insights?metric={metrics}&access_token={tok}")
        if "data" in r: return {m["name"]: m["values"][0]["value"] for m in r["data"] if m.get("values")}
    return {}
def instagram():
    tok, uid = os.environ.get("IG_ACCESS_TOKEN"), os.environ.get("IG_USER_ID")
    if not tok or not uid: print("instagram: no secrets, skipping"); return None
    me = get(f"{IG}/me?fields=username,followers_count,follows_count,media_count&access_token={tok}")
    if "error" in me: return {"error": me["error"]}
    out = {k: me.get(k) for k in ("username", "followers_count", "media_count")}
    posted = json.load(open(os.path.join(ROOT, "instagram/posted.json")))
    out["posts"] = []
    for p in posted:
        info = get(f"{IG}/{p['media_id']}?fields=permalink,like_count,comments_count&access_token={tok}")
        kind = "reel" if p["id"].startswith("reel-") else "post"
        out["posts"].append({"id": p["id"], "type": kind, "posted": p["at"][:10], "permalink": info.get("permalink"),
                             "likes": info.get("like_count"), "comments": info.get("comments_count"),
                             **insights(p["media_id"], kind, tok)})
    return out
def etsy():
    key = os.environ.get("ETSY_API_KEY")
    if not key: print("etsy: no ETSY_API_KEY secret, skipping"); return None
    h = {"x-api-key": key}
    shops = get(f"{ETSY}/shops?shop_name={SHOP}", h)
    if "error" in shops or not shops.get("results"): return {"error": shops.get("error", "shop not found")}
    s = shops["results"][0]
    out = {"sales_total": s.get("transaction_sold_count"), "shop_favorites": s.get("num_favorers"),
           "active_listings": s.get("listing_active_count"), "listings": []}
    r = get(f"{ETSY}/shops/{s['shop_id']}/listings/active?limit=100", h)
    for l in r.get("results", []):
        out["listings"].append({"listing_id": l["listing_id"], "title": l["title"][:60],
                                "views": l.get("views"), "favorites": l.get("num_favorers")})
    return out
def main():
    today = datetime.datetime.utcnow().date().isoformat()
    snap = {"date": today, "instagram": instagram(), "etsy": etsy(),
            "pinterest": None}   # Pinterest analytics needs an approved API app; until then read them in Pinterest Analytics
    os.makedirs(os.path.join(ROOT, "metrics"), exist_ok=True)
    for name in (today, "latest"):
        json.dump(snap, open(os.path.join(ROOT, f"metrics/{name}.json"), "w"), indent=1, ensure_ascii=False)
    print(json.dumps(snap, indent=1, ensure_ascii=False)[:3000])
if __name__ == "__main__": main()

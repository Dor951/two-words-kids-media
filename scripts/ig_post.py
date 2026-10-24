"""Post the next due Instagram image (one per day at most) from instagram/schedule.json, at most one per run.
A post is due when its date and time_utc have passed, it has no "hold", and it is not in posted.json.
Env: IG_ACCESS_TOKEN, IG_USER_ID (Instagram API with Instagram Login). Run: python3 scripts/ig_post.py [--dry-run | --probe]"""
import json, os, sys, time, datetime, urllib.request, urllib.parse, urllib.error
API = "https://graph.instagram.com/v21.0"
RAW = "https://raw.githubusercontent.com/Dor951/two-words-kids-media/main/"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = os.path.join(ROOT, "instagram/posted.json")
def call(method, url, params=None):
    data = urllib.parse.urlencode(params).encode() if params else None
    req = urllib.request.Request(url, data=data, method=method)
    try:
        with urllib.request.urlopen(req, timeout=120) as r: return json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:600]; print("HTTP", e.code, url.split("?")[0], body); return {"error": body}
def due(posts, done, now):
    for p in posts:
        at = datetime.datetime.fromisoformat(f"{p['date']}T{p.get('time_utc', '17:00')}")
        if p["id"] not in done and not p.get("hold") and at <= now: return p
def probe():
    tok = os.environ.get("IG_ACCESS_TOKEN")
    if not tok: raise SystemExit("IG_ACCESS_TOKEN secret is missing")
    me = call("GET", f"{API}/me?fields=user_id,username&access_token={tok}")
    if "username" not in me: raise SystemExit("token does not work")
    print("token ok for", me["username"], "user_id", me.get("user_id"), "| IG_USER_ID secret:", os.environ.get("IG_USER_ID"))
def main(dry):
    posts = json.load(open(os.path.join(ROOT, "instagram/schedule.json")))["posts"]
    log = json.load(open(LOG)); done = {e["id"] for e in log}
    now = datetime.datetime.utcnow()
    if log and (now - datetime.datetime.fromisoformat(log[-1]["at"].rstrip("Z"))).total_seconds() < 10 * 3600:
        print("skip: posted within the last 10h"); return   # backup cron must not double-post
    p = due(posts, done, now)
    if not p: print("nothing due"); return
    if dry: print("dry run, next due:", p["id"], RAW + p["image"]); return
    tok, uid = os.environ.get("IG_ACCESS_TOKEN"), os.environ.get("IG_USER_ID")
    if not tok or not uid: print("no IG_ACCESS_TOKEN / IG_USER_ID secrets yet, skipping"); return
    base = {"image_url": RAW + p["image"], "caption": p["caption"], "access_token": tok}
    c = call("POST", f"{API}/{uid}/media", {**base, "alt_text": p["alt_text"]})
    if "id" not in c: c = call("POST", f"{API}/{uid}/media", base)   # retry without alt text
    if "id" not in c: raise SystemExit("could not create media container")
    for _ in range(20):
        st = call("GET", f"{API}/{c['id']}?fields=status_code&access_token={tok}").get("status_code")
        if st == "FINISHED": break
        if st == "ERROR": raise SystemExit("container error")
        time.sleep(10)
    pub = call("POST", f"{API}/{uid}/media_publish", {"creation_id": c["id"], "access_token": tok})
    if "id" not in pub: raise SystemExit("publish failed")
    log.append({"id": p["id"], "media_id": pub["id"], "at": datetime.datetime.utcnow().isoformat() + "Z"})
    json.dump(log, open(LOG, "w"), indent=1)
    print("published", p["id"], pub["id"])
    # long-lived tokens last 60 days; refreshing keeps the same token alive
    r = call("GET", f"{API.rsplit('/', 1)[0]}/refresh_access_token?grant_type=ig_refresh_token&access_token={tok}")
    if r.get("access_token") and r["access_token"] != tok: print("WARNING: token changed, update the IG_ACCESS_TOKEN secret")
if __name__ == "__main__": probe() if "--probe" in sys.argv else main("--dry-run" in sys.argv)

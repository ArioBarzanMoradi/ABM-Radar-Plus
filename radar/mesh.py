"""Peer observability mesh. Only locally owned readings are exported; no recursive replication."""
import concurrent.futures
import json
import secrets
import threading
from urllib.parse import urlsplit
import urllib.error
import urllib.request

from .common import Problem, digest, now, rid, string, host, one, COUNTRIES, obj, items, jsonstr, uid, test_input
from .observations import number, system, probes
from .database import bump
STALE=90000
MAX_BODY=2*1024*1024

def panel_url(value, empty=False):
    value=string(value,500,not empty).rstrip("/")
    if not value and empty:return ""
    from re import fullmatch
    try: u=urlsplit(value);port=u.port
    except ValueError:raise Problem("پورت نشانی پنل معتبر نیست.") from None
    if not u.hostname or u.username or u.password or u.query or u.fragment or not fullmatch(r"(?:/[A-Za-z0-9_-]+)*",u.path):
        raise Problem("نشانی کامل پنل و WebPath را وارد کنید.")
    if u.scheme!="https" and not (u.scheme=="http" and u.hostname in ("127.0.0.1","localhost","::1")):
        raise Problem("ارتباط گره‌های راه‌دور به HTTPS معتبر نیاز دارد.")
    if port is not None and not 1<=port<=65535:raise Problem("پورت معتبر نیست.")
    return value

def token_auth(db, authorization, test=False):
    node=db.execute("SELECT * FROM mesh_node WHERE id=1").fetchone()
    raw=authorization[7:] if authorization.startswith("Bearer ") else ""
    if not 32<=len(raw)<=128 or not node["token"] or not secrets.compare_digest(digest(raw),node["token"]):
        raise Problem("کلید ارتباط بین پنل‌ها معتبر نیست.",401)
    if test and not node["allow_tests"]:raise Problem("این کلید فقط اجازهٔ خواندن پایش را دارد.",403)
    return node

def export(db):
    from .workspace import snapshot
    local=db.execute("SELECT * FROM mesh_node WHERE id=1").fetchone()
    snap=snapshot(db);hosts=[]
    for s in snap["space"]["servers"][:64]:
        m=snap["telemetry"]["metrics"][s["id"]]
        ext=m.get("system")
        if ext:
            ext={**ext,"listeners":ext["listeners"][:80],"vpn":ext["vpn"][:20],"network":{**ext["network"],"interfaces":ext["network"]["interfaces"][:8]}}
        hosts.append(dict(id=s["id"],name=s["name"],host=s["host"],country=s["country"],online=m["online"],lastSeen=m["lastSeen"],cpu=m["cpu"],ram=m["ram"],ping=m["ping"],system=ext,probes=m.get("probes"),tests=s["tests"][:3],pendingTests=s["pendingTests"]))
    data=dict(protocol=1,node=dict(id=local["node_id"],name=local["name"],url=local["url"]),allowTests=bool(local["allow_tests"]),at=now(),hosts=hosts)
    if len(jsonstr(data).encode())>MAX_BODY:raise Problem("حجم خروجی شبکه از حد مجاز بیشتر است.",503)
    return data

def validate_export(value):
    v=obj(value)
    if v.get("protocol")!=1:raise Problem("نسخهٔ پروتکل گره سازگار نیست.")
    n=obj(v.get("node"))
    node=dict(id=rid(n.get("id")),name=string(n.get("name")),url=panel_url(n.get("url",""),True))
    hosts=[]
    for row in items(v.get("hosts"),64):
        s=obj(row);tests=[]
        for test in items(s.get("tests",[]),3):
            t=obj(test)
            if type(t.get("ok")) is not bool:raise Problem("نتیجهٔ تست گره معتبر نیست.")
            tests.append(dict(id=rid(t.get("id")),at=number(t.get("at")),input=test_input(t.get("input")),ok=t["ok"],inconclusive=t.get("inconclusive") is True,summary=string(t.get("summary",""),600,False),lines=[string(l,400,False) for l in items(t.get("lines",[]),24)]))
        if type(s.get("online")) is not bool:raise Problem("وضعیت گره معتبر نیست.")
        hosts.append(dict(id=rid(s.get("id")),name=string(s.get("name")),host=host(s.get("host")),country=one(s.get("country"),COUNTRIES),online=s["online"],lastSeen=number(s.get("lastSeen")),cpu=number(s.get("cpu"),100),ram=number(s.get("ram"),100),ping=number(s.get("ping"),120000),system=system(s.get("system")),probes=probes(s.get("probes")),tests=tests,pendingTests=number(s.get("pendingTests"),5) or 0))
    return dict(protocol=1,node=node,hosts=hosts,allowTests=v.get("allowTests") is True,at=number(v.get("at")))

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args):raise Problem("گره تغییر مسیر داد؛ نشانی نهایی پنل را ثبت کنید.")

def request(peer,path,body=None):
    headers={"Authorization":"Bearer "+peer["token"],"Accept":"application/json"}
    raw=None
    if body is not None:raw=jsonstr(body).encode();headers["Content-Type"]="application/json"
    req=urllib.request.Request(peer["url"]+path,data=raw,headers=headers)
    with urllib.request.build_opener(NoRedirect()).open(req,timeout=3) as response:
        data=response.read(MAX_BODY+1)
    if len(data)>MAX_BODY:raise Problem("پاسخ گره بیش از حد بزرگ است.")
    return json.loads(data)

def poll_one(store,peer):
    data=None;error=""
    try:
        data=validate_export(request(peer,"/api/mesh/export"))
    except urllib.error.HTTPError as e:error={401:"کلید گره پذیرفته نشد",403:"دسترسی گره مجاز نیست",404:"نشانی پنل یا WebPath درست نیست"}.get(e.code,"پاسخ ناموفق از گره")
    except Problem as e:error=str(e)
    except Exception:error="ارتباط، گواهی TLS یا پاسخ گره در دسترس نیست"
    with store.connection(True) as db:
        # Identity checks share the write transaction; two parallel first polls cannot pin one node twice.
        if data and not error:
            own=db.execute("SELECT node_id FROM mesh_node WHERE id=1").fetchone()[0]
            duplicate=db.execute("SELECT 1 FROM mesh_peers WHERE node_id=? AND id!=?",(data["node"]["id"],peer["id"])).fetchone()
            if data["node"]["id"]==own or duplicate or (peer["node_id"] and peer["node_id"]!=data["node"]["id"]):error="شناسهٔ گره تکراری یا تغییر کرده است."
        if error:
            db.execute("UPDATE mesh_peers SET last_try=?,error=? WHERE id=? AND url=? AND token=?",(now(),error,peer["id"],peer["url"],peer["token"]))
        else:
            db.execute("UPDATE mesh_peers SET last_ok=?,last_try=?,error='',snapshot=?,node_id=? WHERE id=? AND url=? AND token=?",(now(),now(),jsonstr(data),data["node"]["id"],peer["id"],peer["url"],peer["token"]))

def poll(store):
    with store.connection() as db:peers=[dict(r) for r in db.execute("SELECT * FROM mesh_peers")]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda peer:poll_one(store,peer),peers))

def view(db):
    local=export(db);peers=[]
    for p in db.execute("SELECT * FROM mesh_peers ORDER BY rowid"):
        peers.append(dict(id=p["id"],name=p["name"],url=p["url"],lastOk=p["last_ok"],lastTry=p["last_try"],error=p["error"],stale=bool(not p["last_ok"] or now()-p["last_ok"]>=STALE or p["error"]),snapshot=json.loads(p["snapshot"]) if p["snapshot"] else None))
    return dict(local=local,peers=peers,configuredKey=bool(db.execute("SELECT token FROM mesh_node WHERE id=1").fetchone()[0]))

def apply(db,path,data):
    if path=="/api/mesh/local":
        db.execute("UPDATE mesh_node SET name=?,url=? WHERE id=1",(string(data.get("name")),panel_url(data.get("url",""),True)))
    elif path=="/api/mesh/token":
        raw=secrets.token_urlsafe(36)
        if type(data.get("allowTests",False)) is not bool:raise Problem("مجوز تست معتبر نیست.")
        db.execute("UPDATE mesh_node SET token=?,allow_tests=? WHERE id=1",(digest(raw),data.get("allowTests",False)))
        bump(db);return dict(token=raw)
    elif path=="/api/mesh/peer":
        url=panel_url(data.get("url"));name=string(data.get("name"))
        token=string(data.get("token"),128)
        import re
        if not re.fullmatch(r"[A-Za-z0-9_-]{32,128}",token):raise Problem("قالب کلید گره معتبر نیست.")
        if db.execute("SELECT url FROM mesh_node WHERE id=1").fetchone()[0]==url:raise Problem("این نشانی متعلق به همین پنل است.")
        previous=db.execute("SELECT * FROM mesh_peers WHERE url=?",(url,)).fetchone()
        if not previous and db.execute("SELECT count(*) FROM mesh_peers").fetchone()[0]>=16:raise Problem("حداکثر ۱۶ گره قابل اتصال است.")
        if previous:
            db.execute("UPDATE mesh_peers SET name=?,token=?,node_id=NULL,last_ok=NULL,last_try=NULL,error='',snapshot=NULL WHERE id=?",(name,token,previous["id"]))
        else:db.execute("INSERT INTO mesh_peers(id,name,url,token) VALUES(?,?,?,?)",(uid(),name,url,token))
    elif path=="/api/mesh/remove":
        db.execute("DELETE FROM mesh_peers WHERE id=?",(rid(data.get("peerId")),))
    else:raise Problem("عملیات شبکه شناخته نشد.",404)
    bump(db)
    return view(db)

def run_remote(store,data):
    with store.connection() as db:
        row=db.execute("SELECT * FROM mesh_peers WHERE id=?",(rid(data.get("peerId")),)).fetchone()
        if not row:raise Problem("گره پیدا نشد.",404)
        peer=dict(row)
        if not peer["snapshot"] or not json.loads(peer["snapshot"]).get("allowTests"):raise Problem("گره مقصد مجوز اجرای تست نداده است.",403)
    body=dict(id=rid(data.get("id")),serverId=rid(data.get("serverId")),input=test_input(data.get("input")))
    try:request(peer,"/api/mesh/command",body)
    except urllib.error.HTTPError as e:
        raise Problem("گره تست را نپذیرفت؛ کلید، مقصدهای مجاز و اتصال عامل را بررسی کنید.",e.code if e.code in (400,401,403,409,422,429) else 502) from None
    except Exception:raise Problem("درخواست تست به گره نرسید یا پاسخ آن نامشخص است؛ با همان شناسه دوباره تلاش کنید.",502) from None
    return dict(ok=True)


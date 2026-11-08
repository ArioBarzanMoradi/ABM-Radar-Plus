import json

from .common import (
    ALERT_STATES,
    DEFAULT_STEPS,
    LEVELS,
    Problem,
    checklist,
    digest,
    fields,
    items,
    jsonstr,
    now,
    obj,
    one,
    rid,
    string,
    test_input,
)
from .database import alert, bump, config, log
from .observations import monitoring
from .monitor import STALE_MS, history, reading


def snapshot(db):
    at = now()
    hosts = [json.loads(r[0]) for r in db.execute("SELECT config FROM hosts ORDER BY rowid DESC")]
    agents = {r["host"]: r for r in db.execute("SELECT host,last,reading FROM agents")}
    metrics = {}
    for s in hosts:
        obs = reading(s, agents.get(s["id"]), at)
        metrics[s["id"]] = obs
        s["online"] = obs["online"]
        s["tests"] = [
            json.loads(r[0])
            for r in db.execute(
                "SELECT result FROM jobs WHERE host=? AND result IS NOT NULL ORDER BY at DESC LIMIT 100",
                (s["id"],),
            )
        ]
        s["pendingTests"] = db.execute(
            "SELECT count(*) FROM jobs WHERE host=? AND result IS NULL", (s["id"],)
        ).fetchone()[0]
    events = [
        dict(r)
        for r in db.execute(
            "SELECT id,host AS serverId,at,title,body,level FROM events ORDER BY at DESC,rowid DESC LIMIT 2000"
        )
    ]
    alerts = [
        dict(r)
        for r in db.execute(
            "SELECT id,host AS serverId,at,title,body,severity,state FROM alerts ORDER BY at DESC,rowid DESC"
        )
    ]
    meta = db.execute("SELECT * FROM meta WHERE id=1").fetchone()
    return {
        "revision": meta["revision"],
        "space": {
            "servers": hosts,
            "events": events,
            "alerts": alerts,
            "settings": {"auto": bool(meta["auto"]), "interval": meta["interval"]},
        },
        "telemetry": {
            "at": at,
            "source": "agent",
            "metrics": metrics,
            "history": {
                k: history(db, at, n) for k, n in (("6h", 360), ("24h", 1440), ("7d", 10080))
            },
        },
    }


def verify_target(db, target):
    for row in db.execute("SELECT config FROM hosts"):
        cfg = json.loads(row[0])
        if target in [cfg["host"], *cfg["domains"],*[t["host"] for t in cfg.get("monitoring",{}).get("targets",[])]]:
            return
    from urllib.parse import urlsplit
    if any(urlsplit(row[0]).hostname==target for row in db.execute("SELECT url FROM mesh_peers")):return
    raise Problem("برای تست واقعی، مقصد را در نشانی یا دامنه‌های یکی از سرورها ثبت کنید.", 422)


def mutate(db, request_id, c):
    request_id = rid(request_id)
    c = obj(c)
    signature = digest(json.dumps(c, ensure_ascii=False, sort_keys=True))
    seen = db.execute("SELECT signature FROM receipts WHERE id=?", (request_id,)).fetchone()
    if seen:
        if seen[0] != signature:
            raise Problem("شناسهٔ درخواست تکراری است.", 409)
        return
    op = c.get("type")
    t = now()
    if op == "settings.save":
        if type(c.get("auto")) is not bool or c.get("interval") not in (15, 30, 60, 120):
            raise Problem("تنظیمات بازخوانی معتبر نیست.")
        db.execute("UPDATE meta SET auto=?,interval=? WHERE id=1", (c["auto"], c["interval"]))
    elif op == "alert.set":
        a = db.execute("SELECT * FROM alerts WHERE id=?", (rid(c.get("alertId")),)).fetchone()
        state = one(c.get("state"), ALERT_STATES)
        if not a:
            raise Problem("هشدار پیدا نشد.", 404)
        if a["state"] != state:
            db.execute("UPDATE alerts SET state=? WHERE id=?", (state, a["id"]))
            label = {"open": "باز", "tracking": "در پیگیری", "resolved": "رفع‌شده"}[state]
            log(db, a["host"], "وضعیت هشدار به «" + label + "» تغییر کرد", a["title"])
    else:
        identifier = rid(c.get("serverId"))
        if op == "server.delete":
            removed = config(db, identifier)
            if c.get("expected") != removed["editedAt"]:
                raise Problem("پیکربندی تغییر کرده است. فرم را دوباره باز کنید.", 409)
            # Remove peer references and credentials in the same transaction.
            for row in db.execute("SELECT id,config FROM hosts WHERE id!=?", (identifier,)).fetchall():
                peer = json.loads(row["config"])
                changed = False
                for service in peer["services"]:
                    if service.get("peerId") == identifier:
                        service.pop("peerId")
                        changed = True
                if changed:
                    peer["editedAt"] = max(t, peer["editedAt"] + 1)
                    db.execute("UPDATE hosts SET config=? WHERE id=?", (jsonstr(peer), peer["id"]))
                    log(db, peer["id"], "مقصد تونل از پایش حذف شد", removed["name"])
            for table in ("jobs", "samples", "extended_samples", "agents", "alerts", "events"):
                db.execute(f"DELETE FROM {table} WHERE host=?", (identifier,))
            db.execute("DELETE FROM hosts WHERE id=?", (identifier,))
        elif op == "server.save":
            v = fields(c.get("fields"))
            exists = db.execute(
                "SELECT id FROM hosts WHERE address=? AND id!=?", (v["host"], identifier)
            ).fetchone()
            if exists:
                raise Problem("این IP یا نام میزبان قبلاً ثبت شده است.", 409)
            for service in v["services"]:
                peer = service.get("peerId")
                if peer and (
                    peer == identifier
                    or not db.execute("SELECT 1 FROM hosts WHERE id=?", (peer,)).fetchone()
                ):
                    raise Problem("برای تونل یک سرور مقصد دیگر انتخاب کنید.")
            old = db.execute("SELECT config FROM hosts WHERE id=?", (identifier,)).fetchone()
            if old:
                s = json.loads(old[0])
                if c.get("expected") != s["editedAt"]:
                    raise Problem("پیکربندی تغییر کرده است. فرم را دوباره باز کنید.", 409)
                changed = [
                    name
                    for k, name in (
                        ("name", "نام"),
                        ("host", "میزبان"),
                        ("country", "کشور"),
                        ("city", "شهر"),
                        ("group", "گروه"),
                        ("os", "سیستم‌عامل"),
                        ("domains", "دامنه‌ها"),
                        ("ports", "پورت‌ها"),
                        ("services", "سرویس‌ها"),
                    )
                    if s.get(k) != v[k]
                ]
                s.update(v, editedAt=max(t, s["editedAt"] + 1))
                log(db, identifier, "ویرایش پیکربندی سرور", "، ".join(changed))
            else:
                if c.get("expected") is not None:
                    raise Problem("سرور مورد ویرایش پیدا نشد.", 404)
                s = {
                    **v,
                    "id": identifier,
                    "createdAt": t,
                    "editedAt": t,
                    "notes": [],
                    "lists": [checklist("بررسی دسترسی و سرویس", DEFAULT_STEPS)],
                }
                log(db, identifier, "سرور به زیرساخت افزوده شد", v["group"])
            db.execute(
                "INSERT INTO hosts VALUES(?,?,?) ON CONFLICT(id) DO UPDATE SET address=excluded.address,config=excluded.config",
                (identifier, v["host"], jsonstr(s)),
            )
        else:
            s = config(db, identifier)
            if op == "monitoring.save":
                s["monitoring"]=monitoring(c.get("monitoring"))
                db.execute("UPDATE hosts SET config=? WHERE id=?",(jsonstr(s),identifier))
                log(db,identifier,"تنظیمات پایش پروتکل و مقصدها ذخیره شد")
            elif op == "test.run":
                data = test_input(c.get("input"))
                verify_target(db, data["target"])
                a = db.execute("SELECT last FROM agents WHERE host=?", (identifier,)).fetchone()
                if not a or not a[0] or t - a[0] >= STALE_MS:
                    raise Problem("برای تست، ابتدا عامل این سرور را وصل کنید.", 409)
                if (
                    db.execute(
                        "SELECT count(*) FROM jobs WHERE host=? AND result IS NULL", (identifier,)
                    ).fetchone()[0]
                    >= 5
                ):
                    raise Problem("پنج تست در صف این سرور است.", 429)
                db.execute(
                    "INSERT INTO jobs(id,host,at,input) VALUES(?,?,?,?)",
                    (request_id, identifier, t, jsonstr(data)),
                )
                log(db, identifier, "تست شبکه در صف عامل قرار گرفت", data["target"], "info")
            elif op == "event.add":
                title = string(c.get("title"))
                body = string(c.get("body", ""), 2000, False)
                level = one(c.get("level"), LEVELS)
                log(db, identifier, title, body, level)
                if level in ("error", "warning"):
                    alert(db, identifier, title, body, "critical" if level == "error" else "warning")
            else:
                if op == "note.add":
                    s["notes"].insert(
                        0, {"id": request_id, "at": t, "body": string(c.get("body"), 4000)}
                    )
                    log(db, identifier, "یادداشت جدید ثبت شد")
                elif op == "checklist.add":
                    steps = [string(x) for x in items(c.get("steps"), 55)]
                    if not steps:
                        raise Problem("حداقل یک مرحله وارد کنید.")
                    title = string(c.get("title"))
                    s["lists"].append(checklist(title, steps))
                    log(db, identifier, "افزودن چک‌لیست عیب‌یابی", title)
                elif op in ("step.set", "step.add"):
                    lst = next((l for l in s["lists"] if l["id"] == c.get("listId")), None)
                    if not lst:
                        raise Problem("چک‌لیست پیدا نشد.", 404)
                    if op == "step.add":
                        title = string(c.get("title"))
                        lst["steps"].append(dict(id=request_id, title=title, done=False))
                        log(db, identifier, "افزودن مرحله به چک‌لیست", title)
                    else:
                        step = next((v for v in lst["steps"] if v["id"] == c.get("stepId")), None)
                        if not step or type(c.get("done")) is not bool:
                            raise Problem("مرحله معتبر نیست.")
                        if step["done"] != c["done"]:
                            step["done"] = c["done"]
                            log(
                                db,
                                identifier,
                                "مرحله انجام شد" if step["done"] else "مرحله بازگشایی شد",
                                step["title"],
                            )
                else:
                    raise Problem("عملیات ناشناخته است.")
                db.execute("UPDATE hosts SET config=? WHERE id=?", (jsonstr(s), identifier))
    db.execute("INSERT INTO receipts VALUES(?,?)", (request_id, signature))
    bump(db)

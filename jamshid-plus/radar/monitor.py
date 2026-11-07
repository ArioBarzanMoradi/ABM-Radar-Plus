"""Receive measurements over authenticated outbound agent connections."""

import json
import math
import secrets

from .common import (
    CHECKS,
    Problem,
    digest,
    host,
    items,
    jsonstr,
    now,
    obj,
    one,
    portnum,
    rid,
    string,
    uid,
)
from .database import alert, bump, config, log

STALE_MS = 120_000
WEEK = 7 * 86400_000


def issue_token(db, identifier):
    config(db, identifier)
    token = secrets.token_urlsafe(36)
    db.execute(
        """INSERT INTO agents(host,token) VALUES(?,?)
                  ON CONFLICT(host) DO UPDATE SET token=excluded.token""",
        (identifier, digest(token)),
    )
    log(db, identifier, "کلید اتصال عامل صادر شد")
    bump(db)
    return token


def number(value, high):
    if value is None:
        return None
    if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= high:
        raise Problem("مقدار نمونه خارج از محدوده است.")
    return round(value, 1)


def parse_sample(data):
    v = obj(data)
    ports = {}
    for item in items(v.get("ports"), 1200):
        p = obj(item)
        key = one(p.get("protocol"), {"TCP", "UDP"}), portnum(p.get("number"))
        ports[key] = {"protocol": key[0], "number": key[1], "state": "open"}
    services = {}
    for s in items(v.get("services"), 120):
        s = obj(s)
        name = string(s.get("name"))
        services[name] = one(s.get("state"), {"active", "stopped", "degraded", "unknown"})
    coverage = {}
    for proto in ("TCP", "UDP"):
        coverage[proto] = obj(v.get("coverage", {})).get(proto) is True
    return {
        "cpu": number(v.get("cpu"), 100),
        "ram": number(v.get("ram"), 100),
        "ping": number(v.get("ping"), 120000),
        "pingTarget": host(v["pingTarget"]) if v.get("pingTarget") else "",
        "ports": list(ports.values()),
        "coverage": coverage,
        "services": services,
    }


def incident(db, identifier, flags, key, on, title, recovery, body="", severity="warning"):
    before = bool(flags.get(key))
    if before == on:
        return
    flags[key] = on
    if on:
        log(db, identifier, title, body, "error" if severity == "critical" else "warning")
        alert(db, identifier, title, body, severity)
    else:
        log(db, identifier, recovery, body, "info")


def record_sample(db, agent, s, at):
    flags = json.loads(agent["flags"])
    identifier = agent["host"]
    if agent["last"] is None:
        log(db, identifier, "اولین نمونه از عامل لینوکس دریافت شد", level="info")
    incident(db, identifier, flags, "offline", False, "", "ارتباط عامل دوباره برقرار شد")
    for field, upper, lower, name in (("cpu", 85, 75, "پردازنده"), ("ram", 90, 80, "حافظه")):
        value = s[field]
        if value is not None:
            high = value > lower if flags.get(field) else value >= upper
            incident(
                db,
                identifier,
                flags,
                field,
                high,
                "افزایش مصرف " + name,
                "مصرف " + name + " به محدودهٔ عادی برگشت",
                f"{value:.0f}٪",
            )
    prior = json.loads(agent["reading"])["services"] if agent["reading"] else {}
    for name, state in s["services"].items():
        if state not in ("active", "stopped", "degraded"):
            continue
        if prior.get(name) != state:
            incident(
                db,
                identifier,
                flags,
                "svc:" + name,
                state != "active",
                "اختلال در " + name,
                "سرویس دوباره فعال شد",
                name,
            )
    db.execute(
        "UPDATE agents SET last=?,reading=?,flags=? WHERE host=?",
        (at, jsonstr(s), jsonstr(flags), identifier),
    )
    db.execute(
        "INSERT OR REPLACE INTO samples VALUES(?,?,?,?,?)",
        (identifier, at // 60000, s["cpu"], s["ram"], s["ping"]),
    )
    bump(db)


def finish_job(db, row, out, at):
    inp = json.loads(row["input"])
    result = {"id": row["id"], "at": at, "source": "agent", "input": inp, **out}
    db.execute("UPDATE jobs SET result=? WHERE id=?", (jsonstr(result), row["id"]))
    level = "info" if out["ok"] or out["inconclusive"] else "error"
    status = "نامشخص" if out["inconclusive"] else "موفق" if out["ok"] else "ناموفق"
    title = f"تست {CHECKS[inp['kind']]} · {status}"
    log(db, row["host"], title, out["summary"], level)
    if level == "error":
        alert(db, row["host"], title, out["summary"])
    bump(db)


def sync(db, token, payload):
    agent = db.execute("SELECT * FROM agents WHERE token=?", (digest(token),)).fetchone()
    if not agent:
        raise Problem("کلید عامل معتبر نیست.", 401)
    identifier = agent["host"]
    at = now()
    if "sample" in payload:
        record_sample(db, agent, parse_sample(payload["sample"]), at)
    if "result" in payload:
        data = obj(payload["result"])
        job = db.execute(
            "SELECT * FROM jobs WHERE id=? AND host=?", (rid(data.get("id")), identifier)
        ).fetchone()
        if job and not job["result"] and job["lease"] and job["lease"] == data.get("lease"):
            if type(data.get("ok")) is not bool or type(data.get("inconclusive", False)) is not bool:
                raise Problem("نتیجهٔ تست معتبر نیست.")
            finish_job(
                db,
                job,
                {
                    "ok": data["ok"],
                    "inconclusive": data.get("inconclusive", False),
                    "summary": string(data.get("summary"), 600),
                    "lines": [string(line, 400, False) for line in items(data.get("lines"), 24)],
                },
                at,
            )
    cfg = config(db, identifier)
    job = db.execute(
        """SELECT * FROM jobs WHERE host=? AND result IS NULL AND at>? AND
                      (lease_until IS NULL OR lease_until<=?) ORDER BY at LIMIT 1""",
        (identifier, at - 120000, at),
    ).fetchone()
    pending = None
    if job and payload.get("acceptJobs", True) is True:
        lease = uid()
        db.execute("UPDATE jobs SET lease=?,lease_until=? WHERE id=?", (lease, at + 35000, job["id"]))
        pending = {"id": job["id"], "lease": lease, "input": json.loads(job["input"])}
    return {"services": [v["name"] for v in cfg["services"]], "job": pending}


def maintenance(store):
    t = now()
    with store.connection(True) as db:
        for a in db.execute(
            "SELECT host,flags FROM agents WHERE last IS NOT NULL AND last<=?", (t - STALE_MS,)
        ).fetchall():
            flags = json.loads(a["flags"])
            if not flags.get("offline"):
                incident(
                    db,
                    a["host"],
                    flags,
                    "offline",
                    True,
                    "ارتباط با عامل قطع شد",
                    "",
                    "بیش از دو دقیقه از آخرین نمونه گذشته است.",
                    "critical",
                )
                db.execute("UPDATE agents SET flags=? WHERE host=?", (jsonstr(flags), a["host"]))
                bump(db)
        for job in db.execute(
            "SELECT * FROM jobs WHERE result IS NULL AND at<?", (t - 120000,)
        ).fetchall():
            finish_job(
                db,
                job,
                dict(
                    ok=False,
                    inconclusive=True,
                    summary="در مهلت مقرر نتیجه‌ای از عامل دریافت نشد.",
                    lines=[],
                ),
                t,
            )
        db.execute("DELETE FROM samples WHERE minute<?", ((t - WEEK) // 60000,))
        db.execute("DELETE FROM sessions WHERE expires<=?", (t,))
        db.execute("DELETE FROM attempts WHERE start<?", (t - 300000,))


def reading(s, agent, t):
    last = agent["last"] if agent else None
    current = bool(last and t - last < STALE_MS)
    raw = json.loads(agent["reading"]) if agent and agent["reading"] else {}
    observed = {(p["protocol"], p["number"]): p for p in raw.get("ports", [])} if current else {}
    ports = dict(observed)
    for p in s["ports"]:
        key = p["protocol"], p["number"]
        if key not in ports:
            closed = current and raw.get("coverage", {}).get(p["protocol"])
            ports[key] = {**p, "state": "closed" if closed else "unknown"}
    services = [
        {**v, "state": raw.get("services", {}).get(v["name"], "unknown") if current else "unknown"}
        for v in s["services"]
    ]
    return {
        "online": current,
        "awaiting": last is None,
        "paired": bool(agent),
        "lastSeen": last,
        "pingTarget": raw.get("pingTarget", ""),
        "cpu": raw.get("cpu") if current else None,
        "ram": raw.get("ram") if current else None,
        "ping": raw.get("ping") if current else None,
        "ports": sorted(ports.values(), key=lambda p: (p["number"], p["protocol"])),
        "services": services,
        "portCoverage": raw.get("coverage", {}) if current else {},
    }


def history(db, t, minutes):
    # Forty equal time buckets. Average each host within a bucket before averaging the fleet.
    end = t // 60000 + 1
    start = end - minutes
    rows = db.execute(
        """WITH hosts_per_bucket AS (
        SELECT CAST((minute-?)*40/? AS INTEGER) AS b,host,AVG(cpu) AS cpu,AVG(ram) AS ram,AVG(ping) AS ping
        FROM samples WHERE minute>=? AND minute<? GROUP BY b,host)
        SELECT b,AVG(cpu) AS cpu,AVG(ram) AS ram,AVG(ping) AS ping FROM hosts_per_bucket GROUP BY b""",
        (start, minutes, start, end),
    )
    by = {row["b"]: row for row in rows}
    points = []
    for i in range(40):
        row = by.get(i)
        point = {
            "at": min(t, int((start + (i + 0.5) * minutes / 40) * 60000)),
            "online": 0,
            "total": 0,
            "alerts": 0,
        }
        for k in ("cpu", "ram", "ping"):
            point[k] = round(row[k]) if row and row[k] is not None else None
        points.append(point)
    return points

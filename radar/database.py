import hashlib
import hmac
import json
import secrets
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from .common import Problem, digest, now, uid

SCHEMA = """
CREATE TABLE IF NOT EXISTS admin(id INTEGER PRIMARY KEY CHECK(id=1), username TEXT NOT NULL, salt BLOB NOT NULL, password BLOB NOT NULL);
CREATE TABLE IF NOT EXISTS sessions(id TEXT PRIMARY KEY, csrf TEXT NOT NULL, expires INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS attempts(bucket TEXT PRIMARY KEY, start INTEGER NOT NULL, count INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS meta(id INTEGER PRIMARY KEY CHECK(id=1),revision INTEGER NOT NULL,auto INTEGER NOT NULL,interval INTEGER NOT NULL);
INSERT OR IGNORE INTO meta VALUES(1,0,1,30);
CREATE TABLE IF NOT EXISTS hosts(id TEXT PRIMARY KEY,address TEXT NOT NULL UNIQUE, config TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS agents(host TEXT PRIMARY KEY REFERENCES hosts(id),token TEXT NOT NULL UNIQUE,last INTEGER,reading TEXT,flags TEXT NOT NULL DEFAULT '{}');
CREATE TABLE IF NOT EXISTS samples(host TEXT NOT NULL REFERENCES hosts(id),minute INTEGER NOT NULL,cpu REAL,ram REAL,ping REAL,PRIMARY KEY(host,minute));
CREATE INDEX IF NOT EXISTS sample_time ON samples(minute);
CREATE TABLE IF NOT EXISTS events(id TEXT PRIMARY KEY,host TEXT NOT NULL,at INTEGER NOT NULL,title TEXT NOT NULL,body TEXT NOT NULL,level TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS event_time ON events(at DESC);
CREATE TABLE IF NOT EXISTS alerts(id TEXT PRIMARY KEY,host TEXT NOT NULL,at INTEGER NOT NULL,title TEXT NOT NULL,body TEXT NOT NULL,severity TEXT NOT NULL,state TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY,host TEXT NOT NULL REFERENCES hosts(id),at INTEGER NOT NULL,input TEXT NOT NULL,lease TEXT,lease_until INTEGER,result TEXT);
CREATE INDEX IF NOT EXISTS job_host ON jobs(host,at DESC);
CREATE TABLE IF NOT EXISTS extended_samples(host TEXT NOT NULL REFERENCES hosts(id),minute INTEGER NOT NULL,disk REAL,rx REAL,tx REAL,PRIMARY KEY(host,minute));
CREATE TABLE IF NOT EXISTS mesh_node(id INTEGER PRIMARY KEY CHECK(id=1),node_id TEXT NOT NULL,name TEXT NOT NULL,url TEXT NOT NULL,token TEXT,allow_tests INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS mesh_peers(id TEXT PRIMARY KEY,name TEXT NOT NULL,url TEXT NOT NULL UNIQUE,token TEXT NOT NULL,node_id TEXT,last_ok INTEGER,last_try INTEGER,error TEXT NOT NULL DEFAULT '',snapshot TEXT);
CREATE TABLE IF NOT EXISTS receipts(id TEXT PRIMARY KEY,signature TEXT NOT NULL);
"""


class Store:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, mode=0o700, exist_ok=True)
        self.path = self.directory / "radar.sqlite3"
        db = sqlite3.connect(self.path, timeout=10)
        try:
            db.execute("PRAGMA journal_mode=WAL")
            db.executescript(SCHEMA)
            db.execute("INSERT OR IGNORE INTO mesh_node(id,node_id,name,url) VALUES(1,?,?,?)", (uid(),"ABM Radar Plus",""))
            db.commit()
        finally:
            db.close()
        self.path.chmod(0o600)

    @contextmanager
    def connection(self, write=False):
        db = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        db.row_factory = sqlite3.Row
        try:
            db.execute("PRAGMA foreign_keys=ON")
            db.execute("BEGIN IMMEDIATE" if write else "BEGIN")
            yield db
            if db.in_transaction:
                db.commit()
        except BaseException:
            if db.in_transaction:
                db.rollback()
            raise
        finally:
            db.close()


def password_hash(password, salt):
    return hashlib.scrypt(
        password.encode(), salt=salt, n=32768, r=8, p=2, dklen=32, maxmem=96 * 1024 * 1024
    )


def set_admin(store, username, password):
    username = username.strip()
    if not username or len(username) > 64 or not 12 <= len(password) <= 256:
        raise Problem("نام کاربری ۱ تا ۶۴ و گذرواژه ۱۲ تا ۲۵۶ نویسه باشد.")
    salt = secrets.token_bytes(16)
    derived = password_hash(password, salt)
    with store.connection(True) as db:
        db.execute("INSERT OR REPLACE INTO admin VALUES(1,?,?,?)", (username, salt, derived))
        db.execute("DELETE FROM sessions")
        db.execute("DELETE FROM attempts")


def login(store, username, password, ip):
    t = now()
    with store.connection(True) as db:
        admin = db.execute("SELECT * FROM admin WHERE id=1").fetchone()
        if not admin:
            raise Problem("حساب مدیر را از ترمینال سرور ایجاد کنید.", 503)
        bucket = digest(ip)
        attempt = db.execute("SELECT * FROM attempts WHERE bucket=?", (bucket,)).fetchone()
        if attempt and t - attempt["start"] < 300000 and attempt["count"] >= 8:
            raise Problem("تعداد تلاش‌ها زیاد است. پنج دقیقه دیگر تلاش کنید.", 429)
        if not attempt or t - attempt["start"] >= 300000:
            db.execute("INSERT OR REPLACE INTO attempts VALUES(?,?,1)", (bucket, t))
        else:
            db.execute("UPDATE attempts SET count=count+1 WHERE bucket=?", (bucket,))
    # Hash outside SQLite's write lock. Validate the current credential again when issuing a session.
    passed = hmac.compare_digest(password_hash(password, admin["salt"]), admin["password"])
    if not passed or not hmac.compare_digest(username.encode(), admin["username"].encode()):
        raise Problem("نام کاربری یا گذرواژه درست نیست.", 401)
    raw = secrets.token_urlsafe(32)
    csrf = secrets.token_urlsafe(24)
    with store.connection(True) as db:
        row = db.execute("SELECT password FROM admin WHERE id=1").fetchone()
        if not row or not hmac.compare_digest(row[0], admin["password"]):
            raise Problem("ورود را دوباره انجام دهید.", 401)
        db.execute("DELETE FROM attempts WHERE bucket=?", (bucket,))
        db.execute("INSERT INTO sessions VALUES(?,?,?)", (digest(raw), csrf, t + 12 * 3600000))
    return raw, csrf


def session(db, cookie):
    return (
        db.execute(
            "SELECT s.*, a.username FROM sessions s CROSS JOIN admin a WHERE s.id=? AND s.expires>?",
            (digest(cookie), now()),
        ).fetchone()
        if cookie
        else None
    )


def log(db, host, title, body="", level="change", at=None):
    db.execute(
        "INSERT INTO events VALUES(?,?,?,?,?,?)", (uid(), host, at or now(), title, body, level)
    )


def alert(db, host, title, body, severity="warning"):
    db.execute(
        "INSERT INTO alerts VALUES(?,?,?,?,?,?,?)",
        (uid(), host, now(), title, body, severity, "open"),
    )


def bump(db):
    db.execute("UPDATE meta SET revision=revision+1 WHERE id=1")


def config(db, identifier):
    row = db.execute("SELECT config FROM hosts WHERE id=?", (identifier,)).fetchone()
    if not row:
        raise Problem("سرور پیدا نشد.", 404)
    return json.loads(row[0])

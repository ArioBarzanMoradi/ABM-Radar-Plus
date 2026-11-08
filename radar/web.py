"""HTTP boundary. Real workspace data and enrollment are available only to a signed-in operator."""

import hmac
import json
import logging
import mimetypes
from http import HTTPStatus
from http.cookies import SimpleCookie, CookieError
from pathlib import Path
from urllib.parse import urlsplit

from .common import Problem, digest, jsonstr, obj, rid, string
from .database import login, session
from .monitor import issue_token, sync
from .workspace import mutate, snapshot
from . import mesh

ROOT = Path(__file__).resolve().parent.parent
CSP = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'"


class Application:
    def __init__(self, store, public_origin=""):
        self.store = store
        self.origin = public_origin.rstrip("/")
        if self.origin:
            u = urlsplit(self.origin)
            if (
                u.scheme != "https"
                or not u.hostname
                or u.path
                or u.username
                or u.password
                or u.query
                or u.fragment
            ):
                raise ValueError(
                    "RADAR_PUBLIC_ORIGIN must be a single HTTPS origin including its nonstandard port."
                )

    def __call__(self, e, start):
        try:
            status, body, headers = self.dispatch(e)
        except Problem as error:
            status, body, headers = error.status, {"error": str(error)}, []
        except Exception:
            logging.exception("Dashboard request failed")
            status, body, headers = 500, {"error": "پردازش درخواست کامل نشد."}, []
        if isinstance(body, dict):
            body = jsonstr(body).encode()
            headers.append(("Content-Type", "application/json; charset=utf-8"))
        if not any(k == "Cache-Control" for k, _ in headers):
            headers.append(("Cache-Control", "no-store"))
        headers.extend(
            [
                ("Content-Length", str(len(body))),
                ("X-Content-Type-Options", "nosniff"),
                ("Referrer-Policy", "no-referrer"),
                ("Content-Security-Policy", CSP),
                ("X-Frame-Options", "DENY"),
            ]
        )
        start(f"{status} {HTTPStatus(status).phrase}", headers)
        return [body if e["REQUEST_METHOD"] != "HEAD" else b""]

    def request_origin(self, e):
        authority = e.get("HTTP_HOST", "")
        if not authority or any(ch in authority for ch in "/@\\?# \r\n\t"):
            raise Problem("نشانی درخواست معتبر نیست.", 400)
        if self.origin and authority.lower() == urlsplit(self.origin).netloc.lower():
            return self.origin
        try:
            url = urlsplit("http://" + authority)
            _ = url.port
        except ValueError:
            raise Problem("نام میزبان معتبر نیست.", 400) from None
        if url.hostname not in ("localhost", "127.0.0.1", "::1"):
            raise Problem("دامنهٔ پنل را در RADAR_PUBLIC_ORIGIN تنظیم کنید.", 403)
        return "http://" + authority

    @staticmethod
    def payload(e):
        if e.get("CONTENT_TYPE", "").split(";")[0] != "application/json":
            raise Problem("درخواست JSON لازم است.", 415)
        try:
            size = int(e.get("CONTENT_LENGTH") or 0)
        except ValueError:
            raise Problem("اندازهٔ درخواست معتبر نیست.") from None
        if not 0 < size <= 1024 * 1024:
            raise Problem("اندازهٔ درخواست معتبر نیست.", 413)
        try:
            return obj(json.loads(e["wsgi.input"].read(size)))
        except (ValueError, UnicodeError, RecursionError):
            raise Problem("ساختار JSON معتبر نیست.") from None

    @staticmethod
    def cookie(e):
        jar = SimpleCookie()
        try:
            jar.load(e.get("HTTP_COOKIE", ""))
        except CookieError:
            return ""
        return jar["radar_session"].value if "radar_session" in jar else ""

    @staticmethod
    def file(path, private=False):
        if not path.is_file():
            raise Problem("فایل پیدا نشد.", 404)
        mime = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        if path.suffix == ".js":
            mime = "application/javascript"
        if mime.startswith("text/") or mime == "application/javascript":
            mime += "; charset=utf-8"
        return (
            200,
            path.read_bytes(),
            [
                ("Content-Type", mime),
                ("Cache-Control", "no-store" if private else "public, max-age=60"),
            ],
        )

    def dispatch(self, e):
        path = e.get("PATH_INFO", "/")
        method = e["REQUEST_METHOD"]
        origin = self.request_origin(e)
        if method in ("GET", "HEAD"):
            if path == "/healthz":
                return 200, {"status": "ok"}, []
            if path == "/demo.html":
                raise Problem("صفحه پیدا نشد.", 404)
            if path.startswith("/assets/"):
                root = (ROOT / "docs/assets").resolve()
                candidate = (root / path[len("/assets/") :]).resolve()
                if not candidate.is_relative_to(root):
                    raise Problem("فایل پیدا نشد.", 404)
                return self.file(candidate)
            if path in ("/about.html", "/index.html"):
                return self.file(ROOT / "docs/index.html")
            if path=="/api/mesh/export":
                with self.store.connection() as db:
                    mesh.token_auth(db,e.get("HTTP_AUTHORIZATION",""))
                    return 200,mesh.export(db),[]
            with self.store.connection() as db:
                sess = session(db, self.cookie(e))
                if path == "/":
                    return self.file(ROOT / "deploy" / ("panel.html" if sess else "login.html"), True)
                if not sess:
                    raise Problem("برای ورود به پنل احراز هویت کنید.", 401)
                if path == "/api/mesh":
                    return 200,mesh.view(db),[]
                if path == "/api/session":
                    return 200, dict(username=sess["username"], csrf=sess["csrf"]), []
                if path == "/api/workspace":
                    return 200, snapshot(db), []
            raise Problem("صفحه پیدا نشد.", 404)
        if method != "POST":
            raise Problem("روش درخواست مجاز نیست.", 405)
        data = self.payload(e)
        if path == "/api/mesh/command":
            with self.store.connection(True) as db:
                mesh.token_auth(db,e.get("HTTP_AUTHORIZATION",""),True)
                mutate(db,rid(data.get("id")),dict(type="test.run",serverId=rid(data.get("serverId")),input=data.get("input")))
                return 200,dict(ok=True),[]
        if path in ("/api/mesh/refresh","/api/mesh/run"):
            with self.store.connection() as db:
                sess=session(db,self.cookie(e))
                if not sess:raise Problem("ابتدا وارد پنل شوید.",401)
                if not hmac.compare_digest(e.get("HTTP_X_RADAR_CSRF","").encode(),sess["csrf"].encode()):raise Problem("فرم پایان یافته است.",403)
                if e.get("HTTP_ORIGIN") and e["HTTP_ORIGIN"]!=origin:raise Problem("مبدأ نامعتبر است.",403)
            if path=="/api/mesh/run":return 200,mesh.run_remote(self.store,data),[]
            mesh.poll(self.store)
            with self.store.connection() as db:return 200,mesh.view(db),[]
        if path == "/api/agent/sync":
            auth = e.get("HTTP_AUTHORIZATION", "")
            if not auth.startswith("Bearer ") or not 20 < len(auth) < 200:
                raise Problem("کلید عامل لازم است.", 401)
            with self.store.connection(True) as db:
                return 200, sync(db, auth[7:], data), []
        sent_origin = e.get("HTTP_ORIGIN")
        if sent_origin and sent_origin != origin:
            raise Problem("مبدأ درخواست معتبر نیست.", 403)
        secure = "; Secure" if origin.startswith("https:") else ""
        attrs = "; Path=/; HttpOnly; SameSite=Strict" + secure
        if path == "/api/login":
            username = string(data.get("username"), 64)
            password = data.get("password")
            if not isinstance(password, str) or not 0 < len(password) <= 256:
                raise Problem("اطلاعات ورود معتبر نیست.", 401)
            raw, csrf = login(self.store, username, password, e.get("REMOTE_ADDR", "unknown"))
            return (
                200,
                dict(ok=True, csrf=csrf),
                [("Set-Cookie", "radar_session=" + raw + "; Max-Age=43200" + attrs)],
            )
        cookie = self.cookie(e)
        with self.store.connection(True) as db:
            sess = session(db, cookie)
            if not sess:
                raise Problem("نشست پایان یافته است. دوباره وارد شوید.", 401)
            if not hmac.compare_digest(
                e.get("HTTP_X_RADAR_CSRF", "").encode(), sess["csrf"].encode()
            ):
                raise Problem("فرم منقضی شده است. صفحه را تازه کنید.", 403)
            if path == "/api/logout":
                db.execute("DELETE FROM sessions WHERE id=?", (digest(cookie),))
                return 200, dict(ok=True), [("Set-Cookie", "radar_session=; Max-Age=0" + attrs)]
            if path == "/api/agents/issue":
                identifier = rid(data.get("serverId"))
                if (
                    db.execute("SELECT 1 FROM agents WHERE host=?", (identifier,)).fetchone()
                    and data.get("rotate") is not True
                ):
                    raise Problem("برای جایگزینی کلید فعلی، درخواست صدور مجدد را تأیید کنید.", 409)
                return 200, {"token": issue_token(db, identifier)}, []
            if path.startswith("/api/mesh/"):
                return 200,mesh.apply(db,path,data),[]
            if path != "/api/workspace":
                raise Problem("صفحه پیدا نشد.", 404)
            mutate(db, data.get("id"), data.get("command"))
        with self.store.connection() as db:
            return 200, snapshot(db), []

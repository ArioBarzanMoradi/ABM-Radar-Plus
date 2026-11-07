"""Shared validation for dashboard commands and the agent protocol."""

import hashlib
import ipaddress
import json
import re
import time
import uuid

COUNTRIES = {"IR", "DE", "TR", "US", "CH", "CA", "NL", "FR", "GB", "FI", "AE", "SG", "OTHER"}
CHECKS = {"ping": "پینگ", "tcp": "پورت TCP", "udp": "پورت UDP", "dns": "DNS", "trace": "ردیابی مسیر"}
LEVELS = {"error", "warning", "change", "info"}
ALERT_STATES = {"open", "tracking", "resolved"}
DEFAULT_STEPS = [
    "بررسی دسترسی به نشانی سرور",
    "آزمایش پورت سرویس",
    "بررسی وضعیت سرویس و تونل",
    "ثبت نتیجهٔ بررسی",
]
LABEL = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\Z")
DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


class Problem(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def now():
    return int(time.time() * 1000)


def uid():
    return str(uuid.uuid4())


def jsonstr(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"))


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def obj(v):
    if not isinstance(v, dict):
        raise Problem("ساختار داده معتبر نیست.")
    return v


def string(v, limit=100, required=True):
    if not isinstance(v, str) or len(v.strip()) > limit or (required and not v.strip()):
        raise Problem("متن واردشده خالی یا طولانی است.")
    return v.strip()


def one(v, options):
    if not isinstance(v, str) or v not in options:
        raise Problem("گزینهٔ انتخابی معتبر نیست.")
    return v


def items(v, limit):
    if not isinstance(v, list) or len(v) > limit:
        raise Problem("تعداد موارد واردشده معتبر نیست.")
    return v


def rid(v):
    try:
        return str(uuid.UUID(v))
    except (ValueError, AttributeError, TypeError):
        raise Problem("شناسهٔ رکورد معتبر نیست.") from None


def portnum(v):
    if type(v) is not int or not 1 <= v <= 65535:
        raise Problem("پورت باید بین ۱ و ۶۵۵۳۵ باشد.")
    return v


def host(v):
    v = string(v, 253).translate(DIGITS).rstrip(".")
    if v.startswith("[") and v.endswith("]"):
        v = v[1:-1]
    if "%" in v:
        raise Problem("نشانی میزبان معتبر نیست.")
    try:
        return str(ipaddress.ip_address(v))
    except ValueError:
        pass
    try:
        ascii_name = v.encode("idna").decode("ascii").lower()
    except UnicodeError:
        raise Problem("نام دامنه معتبر نیست.") from None
    if (
        len(ascii_name) > 253
        or re.fullmatch(r"[.0-9]+", ascii_name)
        or not all(LABEL.fullmatch(x) for x in ascii_name.split("."))
    ):
        raise Problem("یک IP یا نام میزبان معتبر وارد کنید.")
    return ascii_name


def unique(values):
    if len(values) != len(set(values)):
        raise Problem("رکورد تکراری را حذف کنید.")


def fields(v):
    v = obj(v)
    domains = [host(x) for x in items(v.get("domains"), 100)]
    unique(domains)
    ports, services = [], []
    for p in items(v.get("ports"), 150):
        p = obj(p)
        ports.append(
            dict(
                number=portnum(p.get("number")),
                protocol=one(p.get("protocol"), {"TCP", "UDP"}),
                state="unknown",
            )
        )
    unique([(p["number"], p["protocol"]) for p in ports])
    for s in items(v.get("services"), 100):
        s = obj(s)
        svc = dict(
            name=string(s.get("name")), kind=one(s.get("kind"), {"service", "tunnel"}), state="active"
        )
        if s.get("peerId"):
            if svc["kind"] != "tunnel":
                raise Problem("مقصد فقط برای تونل قابل ثبت است.")
            svc["peerId"] = rid(s["peerId"])
        services.append(svc)
    unique([s["name"].casefold() for s in services])
    return dict(
        name=string(v.get("name")),
        host=host(v.get("host")),
        country=one(v.get("country"), COUNTRIES),
        city=string(v.get("city", ""), 65, False),
        group=string(v.get("group", ""), 65, False),
        os=string(v.get("os", ""), 70, False),
        domains=domains,
        ports=ports,
        services=services,
        online=False,
    )


def test_input(v):
    v = obj(v)
    kind = one(v.get("kind"), CHECKS)
    result = {"kind": kind, "target": host(v.get("target"))}
    if kind in ("tcp", "udp"):
        result["port"] = portnum(v.get("port"))
    return result


def checklist(title, steps):
    return {
        "id": uid(),
        "title": title,
        "steps": [{"id": uid(), "title": s, "done": False} for s in steps],
    }

#!/usr/bin/env python3
"""Unprivileged outbound Linux telemetry collector. Only fixed, typed diagnostics are accepted."""

import argparse
import getpass
import ipaddress
import json
import logging
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from urllib.parse import urlsplit

L = logging.getLogger("radar-agent")


def safe_target(raw):
    if not isinstance(raw, str) or not raw or len(raw) > 253 or any(x in raw for x in "/@?#%\\"):
        raise ValueError("نشانی مقصد معتبر نیست.")
    value = raw.rstrip(".")
    if value.startswith("[") and value.endswith("]"):
        value = value[1:-1]
    try:
        return str(ipaddress.ip_address(value))
    except ValueError:
        pass
    value = value.encode("idna").decode().lower()
    if not all(re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", p) for p in value.split(".")):
        raise ValueError("نام میزبان معتبر نیست.")
    return value


def approved_address(address):
    ip = ipaddress.ip_address(address)
    check = ip.ipv4_mapped if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped else ip
    return not (
        check.is_link_local
        or check.is_multicast
        or check.is_unspecified
        or str(check) == "255.255.255.255"
    )


def bounded_cmd(args, seconds):
    p = subprocess.run(
        args,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=seconds,
        env={**os.environ, "LC_ALL": "C"},
        check=False,
    )
    return p.returncode, p.stdout.decode(errors="replace")[:6400]


def ping(address):
    binary = shutil.which("ping")
    if not binary:
        return None
    code, text = bounded_cmd([binary, "-n", "-c", "1", "-W", "2", address], 3)
    val = re.search(r"time[=<]([\d.]+)\s*ms", text)
    return round(float(val[1]), 1) if not code and val else None


def diagnostic(test):
    kind, target = test["kind"], safe_target(test["target"])

    def result(ok, summary, lines=(), unknown=False):
        return dict(ok=ok, inconclusive=unknown, summary=summary, lines=list(lines)[:18])

    infos = socket.getaddrinfo(target, None, type=socket.SOCK_STREAM)
    addresses = list(dict.fromkeys(i[4][0] for i in infos))
    if kind == "dns":
        return result(True, "پاسخ سامانهٔ نام میزبان دریافت شد.", addresses[:8])
    safe = [ip for ip in addresses if approved_address(ip)]
    if not safe:
        return result(False, "این مقصد محلی ویژه برای تست مجاز نیست.", unknown=True)
    ip = safe[0]
    if kind == "ping":
        if not shutil.which("ping"):
            return result(False, "ابزار ping روی عامل نصب نشده است.", unknown=True)
        delay = ping(ip)
        return result(
            delay is not None,
            "پاسخ ICMP دریافت شد." if delay is not None else "در مهلت تست پاسخ ICMP دریافت نشد.",
            [f"{ip} · {delay} ms" if delay is not None else ip],
        )
    if kind == "trace":
        binary = shutil.which("traceroute")
        if not binary:
            return result(False, "برای این تست بستهٔ traceroute را روی عامل نصب کنید.", unknown=True)
        _, out = bounded_cmd(
            [binary, "-6" if ":" in ip else "-4", "-n", "-m", "10", "-q", "1", "-w", "1", ip], 14
        )
        lines = [line.strip()[:260] for line in out.splitlines() if line.strip()][:14]
        reached = any(
            len(p) > 1 and p[0].isdigit() and p[1] == ip for p in (line.split() for line in lines)
        )
        return result(
            reached,
            "مسیر تا مقصد ثبت شد." if reached else "در محدودهٔ تست، رسیدن به مقصد تأیید نشد.",
            lines,
            not reached,
        )
    if (
        kind not in ("tcp", "udp")
        or type(test.get("port")) is not int
        or not 1 <= test["port"] <= 65535
    ):
        raise ValueError("پارامترهای تست معتبر نیست.")
    port = test["port"]
    family = socket.AF_INET6 if ":" in ip else socket.AF_INET
    with socket.socket(family, socket.SOCK_STREAM if kind == "tcp" else socket.SOCK_DGRAM) as sock:
        sock.settimeout(3)
        start = time.monotonic()
        sock.connect((ip, port))
        if kind == "udp":
            sock.send(b"")
            try:
                sock.recv(256)
            except socket.timeout:
                return result(
                    False,
                    "پاسخ UDP دریافت نشد. وضعیت دسترسی نامشخص است.",
                    [f"{ip} · UDP/{port}"],
                    True,
                )
        delay = (time.monotonic() - start) * 1000
    return result(
        True,
        "اتصال TCP برقرار شد." if kind == "tcp" else "پاسخ UDP دریافت شد.",
        [f"{ip} · {kind.upper()}/{port} · {delay:.1f} ms"],
    )


def do_probe(test):
    try:
        return diagnostic(test)
    except socket.gaierror:
        msg = "سامانهٔ نام میزبان نشانی مقصد را پیدا نکرد."
    except ConnectionRefusedError:
        msg = "مقصد اتصال را رد کرد."
    except (TimeoutError, subprocess.TimeoutExpired):
        msg = "مهلت تست پایان یافت."
    except (KeyError, TypeError, ValueError):
        msg = "پارامترهای تست معتبر نیست."
    except OSError:
        msg = "مسیر شبکه یا مجوز اجرای این تست در دسترس نیست."
    return dict(ok=False, inconclusive=False, summary=msg, lines=[])


def run_probe(test):
    # A separate child bounds DNS resolver and tool latency even if the system resolver stalls.
    try:
        proc = subprocess.run(
            [sys.executable, str(Path(__file__).resolve()), "--probe"],
            input=json.dumps(test),
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=16,
            check=True,
        )
        return json.loads(proc.stdout)
    except (subprocess.SubprocessError, ValueError):
        return dict(
            ok=False, inconclusive=True, summary="عامل در مهلت مقرر نتیجهٔ قطعی دریافت نکرد.", lines=[]
        )


def tick_cpu():
    values = [int(x) for x in Path("/proc/stat").read_text().splitlines()[0].split()[1:9]]
    return sum(values), values[3] + values[4]


def ram_usage():
    m = {
        k: int(v.split()[0])
        for k, v in (line.split(":", 1) for line in Path("/proc/meminfo").read_text().splitlines())
    }
    return round((1 - m["MemAvailable"] / m["MemTotal"]) * 100, 1)


def sockets():
    found = set()
    coverage = {}
    for proto, code in (("TCP", "0A"), ("UDP", "07")):
        complete = True
        for suff in ("", "6"):
            file = Path("/proc/net/" + proto.lower() + suff)
            try:
                lines = file.read_text().splitlines()[1:]
            except FileNotFoundError:
                if not suff or Path("/proc/net/if_inet6").exists():
                    complete = False
                continue
            except OSError:
                complete = False
                continue
            for line in lines:
                cols = line.split()
                if len(cols) > 3 and cols[3] == code:
                    found.add((proto, int(cols[1].split(":")[1], 16)))
        coverage[proto] = complete
    limited = sorted(found)[:1200]
    if len(limited) < len(found):
        coverage = {"TCP": False, "UDP": False}
    return [{"protocol": p, "number": n} for p, n in limited], coverage


def unit_state(unit):
    if (
        not re.fullmatch(r"[A-Za-z0-9_.@:-]{1,150}", unit)
        or unit.startswith("-")
        or not shutil.which("systemctl")
    ):
        return "unknown"
    try:
        _, out = bounded_cmd(
            ["systemctl", "show", unit, "--no-pager", "--property=LoadState,ActiveState"], 2
        )
        props = dict(line.split("=", 1) for line in out.splitlines() if "=" in line)
        if props.get("LoadState") != "loaded":
            return "unknown"
        return {
            "active": "active",
            "inactive": "stopped",
            "failed": "stopped",
            "activating": "degraded",
            "deactivating": "degraded",
        }.get(props.get("ActiveState"), "unknown")
    except (OSError, subprocess.TimeoutExpired):
        return "unknown"


def service_state(name, rules, ports, coverage):
    rule = rules.get(name) or {
        "3x-ui": {"unit": "x-ui.service"},
        "WireGuard": {"interface": "wg0"},
        "Outline": {"unit": "outline-ss-server.service"},
    }.get(name, {})
    if "unit" in rule:
        return unit_state(str(rule["unit"]))
    if "interface" in rule:
        iface = str(rule["interface"])
        if not re.fullmatch(r"[A-Za-z0-9_.-]{1,15}", iface) or iface in (".", ".."):
            return "unknown"
        try:
            return (
                "active"
                if int(Path("/sys/class/net", iface, "flags").read_text().strip(), 16) & 1
                else "stopped"
            )
        except FileNotFoundError:
            return unit_state("wg-quick@" + iface + ".service") if name == "WireGuard" else "unknown"
        except (OSError, ValueError):
            return "unknown"
    if "listen" in rule:
        p = rule["listen"]
        if (
            not isinstance(p, dict)
            or p.get("protocol") not in ("TCP", "UDP")
            or type(p.get("port")) is not int
        ):
            return "unknown"
        if any(x["protocol"] == p["protocol"] and x["number"] == p["port"] for x in ports):
            return "active"
        return "stopped" if coverage.get(p["protocol"]) else "unknown"
    return "unknown"


class Sampler:
    def __init__(self, config):
        self.cfg = config
        self.cpu = tick_cpu()

    def collect(self, names):
        total, idle = tick_cpu()
        delta = total - self.cpu[0]
        usage = (
            round(max(0, min(100, 100 * (1 - (idle - self.cpu[1]) / delta))), 1)
            if delta > 0
            else None
        )
        self.cpu = total, idle
        ports, coverage = sockets()
        target = self.cfg.get("ping_target", "")
        delay = None
        if target and shutil.which("ping"):
            try:
                delay = ping(target)
            except (OSError, subprocess.TimeoutExpired):
                pass
        rules = self.cfg.get("checks", {})
        return dict(
            cpu=usage,
            ram=ram_usage(),
            ping=delay,
            pingTarget=target,
            ports=ports,
            coverage=coverage,
            services=[dict(name=s, state=service_state(s, rules, ports, coverage)) for s in names],
        )


def validate_url(url):
    u = urlsplit(url)
    if not u.hostname or u.username or u.password or u.query or u.fragment or u.path not in ("", "/"):
        raise ValueError("نشانی پایهٔ پنل معتبر نیست.")
    _ = u.port
    if u.scheme != "https" and not (
        u.scheme == "http" and u.hostname in ("127.0.0.1", "::1", "localhost")
    ):
        raise ValueError("اتصال عامل از راه دور به HTTPS نیاز دارد. HTTP فقط در حلقهٔ محلی مجاز است.")
    return url.rstrip("/")


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args):
        raise ValueError("عامل تغییر مسیر پنل را نپذیرفت.")


def exchange(cfg, payload):
    req = urllib.request.Request(
        cfg["panel"] + "/api/agent/sync",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + cfg["token"]},
        method="POST",
    )
    opener = urllib.request.build_opener(NoRedirect())
    with opener.open(req, timeout=12) as response:
        return json.loads(response.read(131072))


def configure(path):
    url = validate_url(
        input("نشانی پایهٔ پنل [http://127.0.0.1:8787]: ").strip() or "http://127.0.0.1:8787"
    )
    token = getpass.getpass("کلید این سرور از صفحهٔ اتصال عامل: ").strip()
    if not re.fullmatch(r"[A-Za-z0-9_-]{32,128}", token):
        raise ValueError("قالب کلید عامل معتبر نیست.")
    target = input(
        "مقصد پینگ ICMP، ترجیحاً یک میزبان ثابت خارج از سرور (Enter برای غیرفعال): "
    ).strip()
    cfg = {
        "panel": url,
        "token": token,
        "ping_target": safe_target(target) if target else "",
        "checks": {},
    }
    if path.exists():
        previous = json.loads(path.read_text())
        cfg["checks"] = previous.get("checks", {})
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(f.name, path)


def run(cfg, once):
    cfg["panel"] = validate_url(cfg["panel"])
    if cfg.get("ping_target"):
        cfg["ping_target"] = safe_target(cfg["ping_target"])
    sampler = Sampler(cfg)
    time.sleep(0.20)  # Two distinct /proc/stat reads are needed for the first CPU percentage.
    names = list(cfg.get("checks", {}))[:100]
    last_sample = 0
    result = None
    failures = 0
    while True:
        try:
            t = time.monotonic()
            payload = {"result": result} if result else {}
            sampled = last_sample == 0 or t - last_sample >= 30
            if sampled:
                payload["sample"] = sampler.collect(names)
            reply = exchange(cfg, payload)
            if sampled:
                last_sample = t
            result = None
            desired = reply.get("services", [])
            if desired != names:
                names = desired
                last_sample = 0
            job = reply.get("job")
            if job:
                result = {"id": job["id"], "lease": job["lease"], **run_probe(job["input"])}
            failures = 0
            if once:
                final = {"acceptJobs": False}
                if result:
                    final["result"] = result
                if last_sample == 0:
                    final["sample"] = sampler.collect(names)
                if len(final) > 1:
                    exchange(cfg, final)
                print("گزارش عامل به پنل رسید.")
                return
        except Exception as err:
            # Never log request headers, enrollment tokens or payload contents.
            failures += 1
            L.warning(
                "Sync failed (%s%s)",
                type(err).__name__,
                f" HTTP {err.code}" if isinstance(err, urllib.error.HTTPError) else "",
            )
            if once:
                raise SystemExit(1)
        time.sleep(min(30, 5 * failures) if failures else 0.3 if result or last_sample == 0 else 5)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--config", type=Path, default=Path("/etc/radar-agent/config.json"))
    p.add_argument("--configure", action="store_true")
    p.add_argument("--once", action="store_true")
    p.add_argument("--probe", action="store_true", help=argparse.SUPPRESS)
    args = p.parse_args()
    try:
        if args.probe:
            print(json.dumps(do_probe(json.load(sys.stdin)), ensure_ascii=False))
        elif args.configure:
            configure(args.config)
        else:
            run(json.loads(args.config.read_text()), args.once)
    except (OSError, ValueError) as e:
        print(f"خطای تنظیمات یا اجرای عامل: {e}", file=sys.stderr)
        sys.exit(1)

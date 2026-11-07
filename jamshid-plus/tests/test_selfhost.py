"""Offline integration checks for the distributed panel, agent and public Pages files."""

import http.cookiejar
import json
import os
from pathlib import Path
import secrets
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request
import uuid

from radar.common import now
from radar.database import Store, set_admin
from radar.monitor import STALE_MS, maintenance

ROOT = Path(__file__).resolve().parents[1]


def new_id():
    return str(uuid.uuid4())


def local_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class NativePanel(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.directory = Path(temp.name)
        self.store = Store(self.directory)
        self.username = "مدیر"
        self.password = secrets.token_urlsafe(22)
        set_admin(self.store, self.username, self.password)
        self.port = local_port()
        self.base = f"http://127.0.0.1:{self.port}"
        self.browser = urllib.request.build_opener(
            urllib.request.ProxyHandler({}),
            urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()),
        )
        self.log = (self.directory / "panel.log").open("w")
        self.addCleanup(self.log.close)
        self.addCleanup(self.stop_panel)
        self.start_panel()

    def start_panel(self):
        self.proc = subprocess.Popen(
            [
                sys.executable,
                str(ROOT / "run.py"),
                "--data-dir",
                str(self.directory),
                "serve",
                "--port",
                str(self.port),
            ],
            stdout=self.log,
            stderr=self.log,
            env={**os.environ, "RADAR_PUBLIC_ORIGIN": "", "PYTHONDONTWRITEBYTECODE": "1"},
        )
        for _ in range(100):
            if self.proc.poll() is not None:
                self.fail((self.directory / "panel.log").read_text())
            try:
                if self.request("/healthz")[0] == 200:
                    return
            except OSError:
                time.sleep(0.05)
        self.fail("Panel did not start")

    def stop_panel(self):
        if self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait(timeout=5)

    def request(self, path, payload=None, headers=None):
        req = urllib.request.Request(
            self.base + path,
            data=None if payload is None else json.dumps(payload).encode(),
            headers={"Content-Type": "application/json", **(headers or {})},
        )
        try:
            response = self.browser.open(req, timeout=6)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            raw = response.read()
            value = (
                json.loads(raw)
                if "application/json" in response.headers.get("Content-Type", "")
                else raw
            )
            return response.code, value, response.headers

    def post(self, path, data, headers=None, status=200):
        code, result, _ = self.request(path, data, {"X-Radar-CSRF": self.csrf, **(headers or {})})
        self.assertEqual(code, status, result)
        return result

    def signin(self):
        data = {"username": self.username, "password": self.password}
        code, reply, headers = self.request("/api/login", data)
        self.assertEqual(code, 200, reply)
        self.assertIn("HttpOnly", headers["Set-Cookie"])
        self.csrf = reply["csrf"]

    def workspace(self):
        code, workspace, _ = self.request("/api/workspace")
        self.assertEqual(code, 200)
        return workspace

    def command(self, command, request_id=None, status=200):
        return self.post(
            "/api/workspace", {"id": request_id or new_id(), "command": command}, status=status
        )

    def register(self, address="127.0.0.1"):
        identifier = new_id()
        fields = {
            "name": "گره آزمایش",
            "country": "DE",
            "host": address,
            "os": "Linux",
            "domains": [],
            "ports": [{"number": self.port, "protocol": "TCP"}],
            "services": [{"name": "وب محلی", "kind": "service"}],
        }
        self.command({"type": "server.save", "serverId": identifier, "fields": fields})
        return identifier, fields

    def run_agent(self, token):
        cfg = self.directory / "collector.json"
        cfg.write_text(
            json.dumps(
                {
                    "panel": self.base,
                    "token": token,
                    "ping_target": "",
                    "checks": {"وب محلی": {"listen": {"protocol": "TCP", "port": self.port}}},
                }
            )
        )
        result = subprocess.run(
            [sys.executable, str(ROOT / "agent/agent.py"), "--config", str(cfg), "--once"],
            env={**os.environ, "NO_PROXY": "127.0.0.1", "no_proxy": "127.0.0.1"},
            text=True,
            capture_output=True,
            timeout=22,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_password_sessions_empty_start_and_public_project(self):
        self.assertEqual(self.request("/api/workspace")[0], 401)
        self.assertIn(b'id="login"', self.request("/")[1])
        self.assertEqual(self.request("/demo.html")[0], 404)
        self.assertIn("جمشید پلاس".encode(), self.request("/about.html")[1])
        self.assertEqual(self.request("/assets/fonts/vazirmatn.woff2")[1][:4], b"wOF2")
        self.assertEqual(
            self.request("/api/login", {"username": self.username, "password": "invalid"})[0], 401
        )
        self.signin()
        self.assertIn(b'id="root"', self.request("/")[1])
        first = self.workspace()
        self.assertEqual(first["space"]["servers"], [])
        self.assertEqual(first["space"]["alerts"], [])
        self.assertEqual(first["space"]["events"], [])
        self.assertEqual(first["telemetry"]["metrics"], {})
        for points in first["telemetry"]["history"].values():
            self.assertTrue(all(p["cpu"] is None and p["ram"] is None and p["ping"] is None for p in points))
        self.assertEqual(self.request("/api/session")[1]["csrf"], self.csrf)
        self.assertEqual(self.request("/api/logout", {})[0], 403)
        self.post("/api/logout", {}, {"Origin": "https://an-unrelated.example"}, 403)
        self.post("/api/logout", {})
        self.assertEqual(self.request("/api/workspace")[0], 401)

    def test_delete_revokes_agent_and_cleans_peer_links_atomically(self):
        self.signin()
        removed, fields = self.register()
        other, other_fields = self.register("localhost")
        other_cfg = next(s for s in self.workspace()["space"]["servers"] if s["id"] == other)
        other_fields["country"] = "CH"
        other_fields["services"].append({"name": "تونل", "kind": "tunnel", "peerId": removed})
        self.command({"type": "server.save", "serverId": other, "expected": other_cfg["editedAt"], "fields": other_fields})
        token = self.post("/api/agents/issue", {"serverId": removed})["token"]
        self.run_agent(token)
        state = self.workspace()
        cfg = next(s for s in state["space"]["servers"] if s["id"] == removed)
        command = {"type": "server.delete", "serverId": removed, "expected": cfg["editedAt"]}
        self.command({**command, "expected": cfg["editedAt"] - 1}, status=409)
        self.assertEqual(len(self.workspace()["space"]["servers"]), 2)
        request_id = new_id()
        after = self.command(command, request_id=request_id)
        self.assertEqual([s["id"] for s in after["space"]["servers"]], [other])
        self.assertNotIn("peerId", after["space"]["servers"][0]["services"][-1])
        self.assertEqual(after["space"]["servers"][0]["country"], "CH")
        self.assertNotIn(removed, after["telemetry"]["metrics"])
        self.assertFalse(any(e["serverId"] == removed for e in after["space"]["events"]))
        repeat = self.command(command, request_id=request_id)
        self.assertEqual(after["revision"], repeat["revision"])
        self.assertEqual(self.request("/api/agent/sync", {}, {"Authorization": "Bearer " + token})[0], 401)
        with self.store.connection() as db:
            for table in ("hosts", "agents", "samples", "jobs", "alerts", "events"):
                column = "id" if table == "hosts" else "host"
                self.assertEqual(db.execute(f"SELECT count(*) FROM {table} WHERE {column}=?", (removed,)).fetchone()[0], 0)

    def test_inventory_retries_checklists_backup_and_restart(self):
        self.signin()
        self.assertEqual(self.workspace()["space"]["servers"], [])
        identifier, fields = self.register()
        original = self.workspace()["space"]["servers"][0]
        note_id = new_id()
        note = {"type": "note.add", "serverId": identifier, "body": "گزارش تست محلی"}
        self.command(note, note_id)
        self.command(note, note_id)
        self.command({**note, "body": "متن متفاوت"}, note_id, 409)
        edit = {
            "type": "server.save",
            "serverId": identifier,
            "fields": {**fields, "group": "شبکه"},
            "expected": original["editedAt"],
        }
        self.command(edit)
        self.command(edit, status=409)
        self.command({"type": "server.save", "serverId": new_id(), "fields": fields}, status=409)
        self.command(
            {
                "type": "checklist.add",
                "serverId": identifier,
                "title": "پایش",
                "steps": ["دسترسی محلی", "ثبت نتیجه"],
            }
        )
        block = self.workspace()["space"]["servers"][0]["lists"][-1]
        self.command(
            {
                "type": "step.set",
                "serverId": identifier,
                "listId": block["id"],
                "stepId": block["steps"][0]["id"],
                "done": True,
            }
        )
        before = self.workspace()
        m = before["telemetry"]["metrics"][identifier]
        self.assertTrue(m["awaiting"])
        self.assertFalse(m["online"])
        self.assertIsNone(m["cpu"])
        self.assertEqual(before["telemetry"]["source"], "agent")
        self.assertEqual(len(before["space"]["servers"][0]["notes"]), 1)
        backup = self.directory / "safe-copy.sqlite3"
        cmd = [
            sys.executable,
            str(ROOT / "run.py"),
            "--data-dir",
            str(self.directory),
            "backup",
            str(backup),
        ]
        subprocess.run(cmd, check=True, capture_output=True, timeout=8)
        self.assertNotEqual(subprocess.run(cmd, capture_output=True, timeout=8).returncode, 0)
        with sqlite3.connect(backup) as db:
            self.assertEqual(db.execute("PRAGMA integrity_check").fetchone()[0], "ok")
            host = json.loads(
                db.execute("SELECT config FROM hosts WHERE id=?", (identifier,)).fetchone()[0]
            )
            self.assertTrue(host["lists"][-1]["steps"][0]["done"])
        self.stop_panel()
        self.start_panel()
        self.assertEqual(self.workspace()["space"], before["space"])

    @unittest.skipUnless(Path("/proc/net/tcp").exists(), "A Linux network namespace is required")
    def test_linux_agent_live_sample_jobs_alerts_and_isolation(self):
        self.signin()
        first, _ = self.register()
        second, _ = self.register("192.0.2.20")

        def issue(host):
            return self.post("/api/agents/issue", {"serverId": host})["token"]

        token, other = issue(first), issue(second)
        self.post("/api/agents/issue", {"serverId": first}, status=409)

        def sync(key, payload):
            return self.request("/api/agent/sync", payload, {"Authorization": "Bearer " + key})

        self.run_agent(token)
        seen = self.workspace()
        metric = seen["telemetry"]["metrics"][first]
        self.assertTrue(metric["online"])
        self.assertTrue(metric["lastSeen"])
        for key in ("cpu", "ram"):
            self.assertTrue(0 <= metric[key] <= 100)
        self.assertIsNone(metric["ping"])
        self.assertIn({"number": self.port, "protocol": "TCP", "state": "open"}, metric["ports"])
        self.assertEqual(metric["services"][0]["state"], "active")
        self.assertTrue(any(p["ram"] is not None for p in seen["telemetry"]["history"]["6h"]))

        def queue(kind, port=None, target="127.0.0.1", status=200):
            identifier = new_id()
            data = {"kind": kind, "target": target}
            if port is not None:
                data["port"] = port
            self.command({"type": "test.run", "serverId": first, "input": data}, identifier, status)
            return identifier

        def server():
            return next(s for s in self.workspace()["space"]["servers"] if s["id"] == first)

        queue("dns", target="not-registered.example", status=422)
        success = queue("tcp", self.port)
        self.assertEqual(server()["pendingTests"], 1)
        self.assertIsNone(sync(other, {})[1]["job"])
        fake = {"id": success, "ok": True, "summary": "fake", "lines": []}
        self.assertEqual(sync(other, {"result": fake})[0], 200)
        self.assertEqual(sync(token, {"result": fake, "acceptJobs": False})[0], 200)
        self.assertEqual(server()["pendingTests"], 1)
        self.run_agent(token)
        self.assertEqual(server()["pendingTests"], 0)
        result = next(t for t in server()["tests"] if t["id"] == success)
        self.assertTrue(result["ok"])
        self.assertEqual(result["source"], "agent")
        # Keep a socket bound without listening so another process cannot claim the closed TCP port.
        with socket.socket() as closed:
            closed.bind(("127.0.0.1", 0))
            failed = queue("tcp", closed.getsockname()[1])
            self.run_agent(token)
        self.assertFalse(next(t for t in server()["tests"] if t["id"] == failed)["ok"])
        workspace = self.workspace()
        alert = next(a for a in workspace["space"]["alerts"] if "TCP" in a["title"])
        for state in ("tracking", "resolved"):
            self.command({"type": "alert.set", "alertId": alert["id"], "state": state})
        with socket.socket(type=socket.SOCK_DGRAM) as silent:
            silent.bind(("127.0.0.1", 0))
            udp = queue("udp", silent.getsockname()[1])
            self.run_agent(token)
        self.assertTrue(next(t for t in server()["tests"] if t["id"] == udp)["inconclusive"])
        self.assertFalse(any("UDP" in a["title"] for a in self.workspace()["space"]["alerts"]))
        with self.store.connection(True) as db:
            db.execute("UPDATE agents SET last=? WHERE host=?", (now() - STALE_MS - 1000, first))
        maintenance(self.store)
        maintenance(self.store)
        snapshot = self.workspace()
        self.assertFalse(snapshot["telemetry"]["metrics"][first]["online"])
        self.assertEqual(
            sum(a["title"] == "ارتباط با عامل قطع شد" for a in snapshot["space"]["alerts"]), 1
        )
        replacement = self.post("/api/agents/issue", {"serverId": first, "rotate": True})["token"]
        self.assertEqual(sync(token, {})[0], 401)
        self.run_agent(replacement)
        self.assertTrue(self.workspace()["telemetry"]["metrics"][first]["online"])
        self.assertTrue(
            any(
                e["title"] == "ارتباط عامل دوباره برقرار شد"
                for e in self.workspace()["space"]["events"]
            )
        )


if __name__ == "__main__":
    unittest.main()

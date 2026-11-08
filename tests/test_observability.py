"""Verify truthful measurements, legacy agents, typed probes and additive migration."""
import json
import os
from pathlib import Path
import socket
import ssl
import http.server
import tempfile
import shutil
import struct
import subprocess
import sys
import threading
import unittest
from unittest.mock import patch

import test_selfhost as native
from agent import agent, network_checks
from agent.system_metrics import SystemSampler, local_ports
from radar.common import Problem, now
from radar.monitor import parse_sample


class Observability(unittest.TestCase):
    @unittest.skipUnless(shutil.which("openssl"), "openssl is needed to create a temporary local test certificate")
    def test_https_validates_certificate_and_tls_reports_expiry(self):
        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200); self.end_headers(); self.wfile.write(b"ok")
            def log_message(self,*args):pass
        with tempfile.TemporaryDirectory() as directory:
            cert,key=Path(directory)/"cert.pem",Path(directory)/"key.pem"
            subprocess.run(["openssl","req","-x509","-newkey","rsa:2048","-nodes","-days","1","-keyout",str(key),"-out",str(cert),"-subj","/CN=localhost","-addext","subjectAltName=DNS:localhost,IP:127.0.0.1"],capture_output=True,check=True,timeout=10)
            context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);context.load_cert_chain(cert,key)
            server=http.server.ThreadingHTTPServer(("127.0.0.1",0),Handler)
            server.socket=context.wrap_socket(server.socket,server_side=True)
            worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
            try:
                with patch.dict(os.environ,{"SSL_CERT_FILE":str(cert)}):
                    self.assertTrue(network_checks.https("localhost",server.server_port)["ok"])
                    self.assertIn("انقضا",network_checks.https("localhost",server.server_port,True)["detail"])
                with patch.dict(os.environ,{"SSL_CERT_FILE":str(Path(directory)/"missing-ca.pem")}):
                    with self.assertRaises(ssl.SSLError):network_checks.https("localhost",server.server_port)
            finally:server.shutdown();server.server_close();worker.join(2)

    def test_linux_system_sample_and_rate_interval(self):
        sampler = SystemSampler()
        first = sampler.collect()
        self.assertGreater(first["disk"]["total"], 0)
        self.assertTrue(0 <= first["disk"]["percent"] <= 100)
        self.assertGreater(first["uptime"], 0)
        self.assertTrue(first["hostname"])
        self.assertIsNone(first["network"]["rxBps"])
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            listener.listen()
            rows = local_ports()
            self.assertTrue(any(p["number"] == listener.getsockname()[1] and p["address"] == "127.0.0.1" and p["family"] == "IPv4" and p["scope"] == "loopback" for p in rows))
        second = sampler.collect()
        self.assertTrue(all(i["rxBps"] is not None and i["txBps"] is not None for i in second["network"]["interfaces"]))
        with patch("agent.system_metrics.subprocess.run", side_effect=FileNotFoundError):
            minimal = SystemSampler().collect()
        self.assertEqual(minimal["network"]["routes"], {"ipv4": [], "ipv6": []})
        self.assertTrue(minimal["disk"]["total"])

    def test_old_agent_and_extended_telemetry_validation(self):
        old = dict(cpu=12, ram=42, ping=None, ports=[], services=[])
        self.assertIsNone(parse_sample(old)["system"])
        sample = {**old, "system": SystemSampler().collect()}
        self.assertTrue(parse_sample(sample)["system"]["hostname"])
        for bad in (float("nan"), float("inf"), -1, True, 101):
            candidate = json.loads(json.dumps(sample))
            candidate["system"]["disk"]["percent"] = bad
            with self.subTest(bad=bad), self.assertRaises(Problem):
                parse_sample(candidate)

    def test_actual_tcp_and_stun_transaction_validation(self):
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0)); listener.listen()
            self.assertTrue(network_checks.tcp("127.0.0.1", listener.getsockname()[1])["ok"])
        for valid in (True, False):
            with socket.socket(type=socket.SOCK_DGRAM) as sock:
                sock.bind(("127.0.0.1", 0)); sock.settimeout(3)
                def reply():
                    req, address = sock.recvfrom(1024)
                    tx = req[8:20] if valid else bytes(12)
                    sock.sendto(struct.pack("!HHI", 0x101, 0, 0x2112a442) + tx, address)
                worker = threading.Thread(target=reply)
                worker.start()
                result = network_checks.stun("127.0.0.1", sock.getsockname()[1])
                worker.join(4)
                self.assertEqual(result["ok"], valid)
                self.assertEqual(result["inconclusive"], not valid)

    def test_missing_ping_is_unknown_and_dns_child_is_bounded(self):
        with patch("agent.agent.shutil.which", return_value=None):
            result = agent.diagnostic({"kind": "ping", "target": "127.0.0.1"})
        self.assertFalse(result["ok"])
        self.assertTrue(result["inconclusive"])
        with patch("agent.agent.subprocess.run", side_effect=subprocess.TimeoutExpired("probe", 4)):
            self.assertFalse(agent.run_probe({"kind": "dns", "target": "example.com"}, 4)["ok"])
        calls = []
        def probe(test):
            calls.append(test)
            return dict(ok=test["kind"]=="tcp", inconclusive=False, summary="TCP" if test["kind"]=="tcp" else "No ICMP", lines=[])
        result = network_checks.collect(probe, [{"name": "own", "host": "127.0.0.1", "port": 42}])
        self.assertTrue(result["targets"][0]["tcp"]["ok"])
        self.assertFalse(result["targets"][0]["icmp"]["ok"])
        self.assertEqual(result["checks"], {})
        self.assertEqual(len(calls), 2)


class ObservationHTTP(unittest.TestCase):
    def setUp(self):
        self.p = native.NativePanel(methodName="runTest")
        self.p.setUp()
        self.addCleanup(self.p.doCleanups)
        self.p.signin()

    def test_agent_receives_monitoring_config_and_persists_extended_history(self):
        p = self.p
        host, _ = p.register()
        token = p.post("/api/agents/issue", {"serverId": host})["token"]
        config = dict(protocolChecks=False, targets=[dict(host="127.0.0.1", name="local TCP", port=p.port)])
        p.command(dict(type="monitoring.save", serverId=host, monitoring=config))
        p.run_agent(token)
        data = p.workspace()
        reading = data["telemetry"]["metrics"][host]
        self.assertTrue(reading["system"]["hostname"])
        self.assertTrue(reading["probes"]["targets"][0]["tcp"]["ok"])
        self.assertTrue(any(row["disk"] is not None for row in data["telemetry"]["history"]["6h"]))
        self.assertEqual(data["space"]["servers"][0]["monitoring"], config)
        p.stop_panel(); p.start_panel()
        self.assertEqual(p.workspace()["space"]["servers"][0]["monitoring"], config)
        # A legacy payload can still sync after a new panel has migrated its schema.
        self.assertEqual(p.request("/api/agent/sync", {"sample":dict(cpu=5, ram=10, ping=None, ports=[], services=[])}, {"Authorization":"Bearer "+token})[0], 200)

    def test_cli_session_rotation_keeps_credentials_and_data(self):
        p = self.p
        p.register()
        command = [sys.executable, str(native.ROOT/"run.py"), "--data-dir", str(p.directory)]
        report = subprocess.run(command+["show"], capture_output=True, text=True, check=True).stdout
        self.assertIn("ABM Radar Plus 2.0.0", report)
        self.assertIn("Servers: 1", report)
        subprocess.run(command+["rotate-sessions"], capture_output=True, check=True)
        self.assertEqual(p.request("/api/workspace")[0], 401)
        p.signin()
        self.assertEqual(len(p.workspace()["space"]["servers"]), 1)

    def test_old_plus_schema_migrates_without_resetting_accounts_keys_or_notes(self):
        p=self.p
        host,_=p.register()
        token=p.post("/api/agents/issue",{"serverId":host})["token"]
        p.command({"type":"note.add","serverId":host,"body":"preserve this note"})
        before=p.workspace()["space"]
        p.stop_panel()
        with p.store.connection(True) as db:
            # These are the only new tables; the remaining schema is the prior Plus layout.
            for table in ("mesh_node","mesh_peers","extended_samples"):db.execute("DROP TABLE "+table)
            credentials=tuple(db.execute("SELECT * FROM admin").fetchone())
        p.start_panel()
        self.assertEqual(p.workspace()["space"],before)
        p.run_agent(token)
        self.assertTrue(p.workspace()["telemetry"]["metrics"][host]["online"])
        with p.store.connection() as db:
            self.assertEqual(tuple(db.execute("SELECT * FROM admin").fetchone()),credentials)
            self.assertEqual(db.execute("SELECT count(*) FROM mesh_node").fetchone()[0],1)


if __name__ == "__main__":
    unittest.main()

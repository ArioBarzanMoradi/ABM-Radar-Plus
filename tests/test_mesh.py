"""Exercise independent panels over real HTTP, including cached partition behavior."""
import json
import secrets
import unittest
from unittest.mock import patch

import test_selfhost as native
from radar import mesh
from radar.common import now, Problem


class MeshIntegration(unittest.TestCase):
    def panel(self):
        p = native.NativePanel(methodName="runTest")
        p.setUp()
        self.addCleanup(p.doCleanups)
        p.signin()
        return p

    def link(self, origin, target, tests=False):
        key = target.post("/api/mesh/token", {"allowTests": tests})["token"]
        result = origin.post("/api/mesh/peer", {"name": "Other panel", "url": target.base, "token": key})
        return key, result["peers"][-1]["id"]

    def test_local_only_exports_keys_permissions_and_csrf(self):
        a, b, c = self.panel(), self.panel(), self.panel()
        ha, _ = a.register()
        hb, _ = b.register()
        hc, _ = c.register()
        self.link(a, b)
        self.link(b, c)
        a.post("/api/mesh/refresh", {})
        b.post("/api/mesh/refresh", {})
        key = a.post("/api/mesh/token", {"allowTests": False})["token"]
        status, export, _ = a.request("/api/mesh/export", headers={"Authorization": "Bearer " + key})
        self.assertEqual(status, 200)
        self.assertEqual([h["id"] for h in export["hosts"]], [ha])
        self.assertNotIn(hb, json.dumps(export))
        self.assertNotIn(hc, json.dumps(export))
        self.assertNotIn(key, json.dumps(export))
        self.assertEqual(a.request("/api/mesh/export")[0], 401)
        self.assertEqual(a.request("/api/mesh/export", headers={"Authorization": "Bearer " + "x" * 48})[0], 401)
        self.assertEqual(a.request("/api/mesh/command", {"id": native.new_id(), "serverId": ha, "input": {"kind": "dns", "target": "127.0.0.1"}}, {"Authorization": "Bearer " + key})[0], 403)
        self.assertEqual(a.request("/api/mesh/token", {"allowTests": True})[0], 403)
        self.assertEqual(a.request("/api/mesh/token", {"allowTests": True}, {"X-Radar-CSRF": a.csrf, "Origin": "https://unrelated.invalid"})[0], 403)
        a.post("/api/mesh/token", {"allowTests": False})
        self.assertEqual(a.request("/api/mesh/export", headers={"Authorization": "Bearer " + key})[0], 401)

    def test_cache_partition_local_independence_and_node_pin(self):
        a, b = self.panel(), self.panel()
        hb, _ = b.register()
        key, peer_id = self.link(a, b)
        result = a.post("/api/mesh/refresh", {})
        peer = result["peers"][0]
        self.assertFalse(peer["stale"])
        self.assertEqual(peer["snapshot"]["hosts"][0]["id"], hb)
        self.assertNotIn(key, json.dumps(result))
        b.stop_panel()
        result = a.post("/api/mesh/refresh", {})
        peer = result["peers"][0]
        self.assertTrue(peer["stale"])
        self.assertTrue(peer["error"])
        self.assertTrue(peer["lastOk"])
        self.assertEqual(peer["snapshot"]["hosts"][0]["id"], hb)
        ha, _ = a.register("192.0.2.10")
        self.assertEqual(a.workspace()["space"]["servers"][0]["id"], ha)
        # A different panel identity at the same URL must not silently replace a pinned peer.
        with b.store.connection(True) as db:
            db.execute("UPDATE mesh_node SET node_id=?", (native.new_id(),))
        b.start_panel()
        result = a.post("/api/mesh/refresh", {})
        self.assertTrue(result["peers"][0]["stale"])
        self.assertIn("شناسه", result["peers"][0]["error"])
        a.post("/api/mesh/peer", {"name": "Repaired", "url": b.base, "token": key})
        self.assertFalse(a.post("/api/mesh/refresh", {})["peers"][0]["stale"])
        self.assertEqual(a.post("/api/mesh/remove", {"peerId": peer_id})["peers"], [])

    def test_scoped_remote_job_is_executed_by_source_agent_once(self):
        a, b = self.panel(), self.panel()
        hb, _ = b.register()
        token = b.post("/api/agents/issue", {"serverId": hb})["token"]
        b.run_agent(token)
        _, peer_id = self.link(a, b, tests=True)
        a.post("/api/mesh/refresh", {})
        job_id = native.new_id()
        command = {"peerId": peer_id, "serverId": hb, "id": job_id, "input": {"kind": "tcp", "target": "127.0.0.1", "port": b.port}}
        a.post("/api/mesh/run", command)
        a.post("/api/mesh/run", command)
        self.assertEqual(b.workspace()["space"]["servers"][0]["pendingTests"], 1)
        self.assertEqual(a.workspace()["space"]["servers"], [])
        b.run_agent(token)
        result = a.post("/api/mesh/refresh", {})
        test = result["peers"][0]["snapshot"]["hosts"][0]["tests"][0]
        self.assertEqual(test["id"], job_id)
        self.assertTrue(test["ok"])
        a.post("/api/mesh/run", {**command, "id": native.new_id(), "input": {"kind": "dns", "target": "not-configured.invalid"}}, status=422)
        b.post("/api/mesh/token", {"allowTests": False})
        a.post("/api/mesh/run", {**command, "id": native.new_id()}, status=401)

    def test_invalid_peer_does_not_destroy_last_good_sample(self):
        a, b = self.panel(), self.panel()
        self.link(a, b)
        a.post("/api/mesh/refresh", {})
        with a.store.connection() as db:
            peer = dict(db.execute("SELECT * FROM mesh_peers").fetchone())
            last_good = peer["snapshot"]
        with patch("radar.mesh.request", return_value={"protocol": 99}):
            mesh.poll_one(a.store, peer)
        with a.store.connection() as db:
            row = db.execute("SELECT * FROM mesh_peers").fetchone()
            self.assertEqual(row["snapshot"], last_good)
            self.assertTrue(row["error"])
        self.assertEqual(a.request("/api/mesh/peer", {"name": "bad", "url": "http://remote.example", "token": "a"*48}, {"X-Radar-CSRF": a.csrf})[0], 400)
        key = a.post("/api/mesh/token", {})["token"]
        a.post("/api/mesh/peer", {"name": "self", "url": a.base, "token": key})
        self.assertTrue(a.post("/api/mesh/refresh", {})["peers"][-1]["stale"])
        with self.assertRaises(Problem):
            mesh.NoRedirect().redirect_request(None, None, None, None, None, None)


if __name__ == "__main__":
    unittest.main()

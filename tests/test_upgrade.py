"""Run the real shell upgrade/rollback logic in a translated, temporary filesystem.

Only absolute installation paths, service management and ownership are substituted.
The Python panel, HTTP health check, SQLite backup, source copies and symlink swap are real.
This needs no root privileges and never operates on the host's systemd or /etc.
"""
import json
import os
from pathlib import Path
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
import unittest
import urllib.request

from radar.database import Store, set_admin

ROOT = Path(__file__).resolve().parents[1]

MOCK = r'''#!/usr/bin/env python3
import os,sys,pathlib,subprocess,signal,time
cmd=pathlib.Path(sys.argv[0]).name
args=sys.argv[1:]
root=pathlib.Path(os.environ['ABM_TEST_ROOT'])
if cmd=='getent':sys.exit(0)
if cmd=='chown':sys.exit(0)
if cmd=='runuser':os.execv(args[args.index('--')+1],args[args.index('--')+1:])
if cmd=='install':
 out=[];i=0
 while i<len(args):
  if args[i] in ('-o','-g'):i+=2
  else:out.append(args[i]);i+=1
 os.execv('/usr/bin/install',['install',*out])
if cmd=='systemctl':
 service=args[-1];agent='agent' in service
 pidfile=root/('agent.pid' if agent else 'panel.pid')
 if args[0]=='is-active':
  if agent:sys.exit(0)
  try:os.kill(int(pidfile.read_text()),0);sys.exit(0)
  except (OSError,ValueError):sys.exit(3)
 if args[0] in ('stop','restart'):
  if pidfile.exists() and not agent:
   try:os.kill(int(pidfile.read_text()),signal.SIGTERM)
   except OSError:pass
   time.sleep(.12)
  fail=root/('fail-agent' if agent else 'fail-panel')
  if args[0]=='restart' and fail.exists():fail.unlink();sys.exit(1)
  if args[0]=='restart' and not agent:
   cfg=dict(line.split('=',1) for line in (root/'etc/radar-infra/panel.env').read_text().splitlines() if '=' in line)
   log=open(root/'service.log','ab')
   p=subprocess.Popen(['/usr/bin/python3',str(root/'opt/radar-infra/current/run.py'),'--data-dir',str(root/'var/lib/radar-infra'),'serve'],env={**os.environ,**cfg},stdout=log,stderr=log)
   pidfile.write_text(str(p.pid))
  sys.exit(0)
 sys.exit(0)
sys.exit(1)
'''


class Upgrade(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)/"host"
        self.source = Path(temp.name)/"source"
        self.root.mkdir()
        shutil.copytree(ROOT, self.source, ignore=shutil.ignore_patterns("node_modules", "__pycache__", "dist", ".git"))
        # Translate literal install locations only; leave the install algorithm and health check intact.
        prefixes = ["/run/systemd/system", "/etc/systemd/system", "/opt/radar-infra", "/opt/radar-agent", "/etc/radar-infra", "/etc/radar-agent", "/var/lib/radar-infra", "/usr/local", "/var/backups/abm-radar-plus", "/opt/abm-radar-plus", "/etc/abm-radar-plus", "/var/lib/abm-radar-plus"]
        for file in (self.source/"install.sh", self.source/"install-agent.sh", self.source/"scripts/update.sh"):
            text=file.read_text()
            for prefix in prefixes:text=text.replace(prefix,str(self.root)+prefix)
            text=text.replace('[[ $EUID == 0 ]]','[[ 1 == 1 ]]').replace('[[ $EUID -eq 0 ]]','[[ 1 == 1 ]]').replace('[[ $EUID == 0 &&','[[ 1 == 1 &&')
            file.write_text(text)
        for directory in ("run/systemd/system", "etc/systemd/system", "etc/radar-infra", "etc/radar-agent", "opt/radar-agent", "opt/radar-infra/releases", "bin"):
            (self.root/directory).mkdir(parents=True,exist_ok=True)
        for command in ("getent","runuser","install","systemctl","chown"):
            p=self.root/"bin"/command;p.write_text(MOCK);p.chmod(0o755)
        self.env={**os.environ,"PATH":str(self.root/"bin")+":"+os.environ["PATH"],"ABM_TEST_ROOT":str(self.root),"PYTHONDONTWRITEBYTECODE":"1"}
        with socket.socket() as s:s.bind(("127.0.0.1",0));self.port=s.getsockname()[1]
        self.config=f"RADAR_PORT={self.port}\nRADAR_PUBLIC_ORIGIN=https://own.example:1453\n"
        (self.root/"etc/radar-infra/panel.env").write_text(self.config)
        self.store=Store(self.root/"var/lib/radar-infra")
        set_admin(self.store,"unchanged-admin","unchanged-test-password")
        self.agent_config='{"panel":"http://127.0.0.1:8788","token":"'+"k"*48+'","ping_target":"1.1.1.1","checks":{}}\n'
        (self.root/"etc/radar-agent/config.json").write_text(self.agent_config)
        (self.root/"opt/radar-agent/agent.py").write_text("# previous collector\n")
        (self.root/"etc/systemd/system/radar-agent.service").write_text("previous agent unit\n")
        previous=self.root/"opt/radar-infra/releases/previous"
        shutil.copytree(self.source,previous,ignore=shutil.ignore_patterns("tests"))
        (previous/"VERSION").write_text("1.2.0\n")
        (self.root/"opt/radar-infra/current").symlink_to(previous,target_is_directory=True)
        shutil.copy2(self.source/"deploy/radar-infra.service",self.root/"etc/systemd/system/radar-infra.service")
        self.addCleanup(self.stop)
        self.call("systemctl","restart","radar-infra.service")

    def call(self,*command,ok=True):
        p=subprocess.run(command,env=self.env,text=True,capture_output=True,timeout=30)
        if ok:self.assertEqual(p.returncode,0,p.stdout+p.stderr)
        return p

    def stop(self):
        self.call("systemctl","stop","radar-infra.service",ok=False)

    def test_update_preserves_identity_and_backup_and_rolls_back_failed_restart(self):
        with self.store.connection() as db:credentials=tuple(db.execute("SELECT * FROM admin").fetchone())
        self.call("bash",str(self.source/"scripts/update.sh"),"--source",str(self.source))
        installed=(self.root/"opt/radar-infra/current").resolve()
        self.assertNotEqual(installed.name,"previous")
        self.assertEqual((installed/"VERSION").read_text().strip(),"2.0.0")
        self.assertEqual(dict(line.split("=",1) for line in (self.root/"etc/radar-infra/panel.env").read_text().splitlines()),dict(line.split("=",1) for line in self.config.splitlines()))
        self.assertEqual((self.root/"etc/radar-agent/config.json").read_text(),self.agent_config)
        with self.store.connection() as db:self.assertEqual(tuple(db.execute("SELECT * FROM admin").fetchone()),credentials)
        backups=list((self.root/"var/backups/abm-radar-plus").glob("*/database.sqlite3"))
        self.assertEqual(len(backups),1)
        with sqlite3.connect(backups[0]) as db:self.assertEqual(db.execute("PRAGMA integrity_check").fetchone()[0],"ok")
        self.assertTrue((self.root/"usr/local/bin/abm-radarctl").is_file())
        self.assertEqual((self.root/"opt/abm-radar-plus").resolve(),self.root/"opt/radar-infra")
        (self.root/"fail-panel").touch()
        failed=self.call("bash",str(self.source/"scripts/update.sh"),"--source",str(self.source),ok=False)
        self.assertNotEqual(failed.returncode,0)
        self.assertEqual((self.root/"opt/radar-infra/current").resolve(),installed)
        # Rollback starts the previous release; the unchanged health URL responds for real.
        import time
        for _ in range(30):
            try:
                with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(f"http://127.0.0.1:{self.port}/healthz",timeout=1) as r:
                    self.assertEqual(json.load(r)["status"],"ok");break
            except OSError:time.sleep(.1)
        else:self.fail("Rollback did not restore HTTP health")
        self.assertEqual(dict(line.split("=",1) for line in (self.root/"etc/radar-infra/panel.env").read_text().splitlines()),dict(line.split("=",1) for line in self.config.splitlines()))

    def test_agent_failure_restores_previous_code_and_reports_partial_upgrade(self):
        (self.root/"fail-agent").touch()
        failed=self.call("bash",str(self.source/"scripts/update.sh"),"--source",str(self.source),ok=False)
        self.assertNotEqual(failed.returncode,0)
        self.assertIn("agent update failed",failed.stderr)
        self.assertEqual((self.root/"opt/radar-agent/agent.py").read_text(),"# previous collector\n")
        self.assertEqual((self.root/"etc/systemd/system/radar-agent.service").read_text(),"previous agent unit\n")
        self.assertEqual((self.root/"etc/radar-agent/config.json").read_text(),self.agent_config)


if __name__=="__main__":unittest.main()

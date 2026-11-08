#!/usr/bin/env python3
"""Run the installed panel or manage its local administrator."""

import argparse
import getpass
import logging
import os
from pathlib import Path
import sqlite3
import sys
import threading
import time

from radar.common import Problem
from radar.database import Store, set_admin
from radar.monitor import maintenance
from radar.web import Application
from radar.mesh import poll as poll_mesh


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description="ABM Radar Plus infrastructure panel")
    parser.add_argument("--data-dir", default=os.getenv("RADAR_DATA", "/var/lib/radar-infra"))
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("init")
    sub.add_parser("set-admin")
    for cmd in ("passwd","username","rotate-sessions","show"):sub.add_parser(cmd)
    backup = sub.add_parser("backup")
    backup.add_argument("destination", type=Path)
    serve = sub.add_parser("serve")
    serve.add_argument("--port", type=int, default=int(os.getenv("RADAR_PORT", "8788")))
    args = parser.parse_args()
    store = Store(args.data_dir)
    if args.action in ("init", "set-admin"):
        with store.connection() as db:
            exists = db.execute("SELECT 1 FROM admin LIMIT 1").fetchone()
        if exists and args.action == "init":
            print("حساب مدیر از قبل آماده است.")
            return
        name = input("نام کاربری مدیر: ").strip()
        password = getpass.getpass("گذرواژه (حداقل ۱۲ نویسه): ")
        if password != getpass.getpass("تکرار گذرواژه: "):
            raise Problem("دو گذرواژه یکسان نیستند.")
        set_admin(store, name, password)
        print("حساب مدیر ذخیره شد.")
    elif args.action=="show":
        print("ABM Radar Plus "+(Path(__file__).parent/"VERSION").read_text().strip())
        with store.connection() as db:
            print("Servers:",db.execute("SELECT count(*) FROM hosts").fetchone()[0])
            print("Peers:",db.execute("SELECT count(*) FROM mesh_peers").fetchone()[0])
    elif args.action=="rotate-sessions":
        with store.connection(True) as db:db.execute("DELETE FROM sessions")
        print("نشست‌ها بسته شدند.")
    elif args.action=="username":
        name=input("نام کاربری جدید: ").strip()
        if not 1<=len(name)<=64:raise Problem("نام کاربری معتبر نیست.")
        with store.connection(True) as db:
            db.execute("UPDATE admin SET username=? WHERE id=1",(name,));db.execute("DELETE FROM sessions")
        print("نام کاربری ذخیره شد.")
    elif args.action=="passwd":
        with store.connection() as db:row=db.execute("SELECT username FROM admin WHERE id=1").fetchone()
        if not row:raise Problem("حساب مدیر وجود ندارد.")
        password=getpass.getpass("گذرواژهٔ جدید: ")
        if password!=getpass.getpass("تکرار گذرواژه: "):raise Problem("گذرواژه‌ها یکسان نیستند.")
        set_admin(store,row[0],password);print("گذرواژه ذخیره شد.")
    elif args.action == "backup":
        dest = args.destination.expanduser().absolute()
        # Reserve the file exclusively so an existing backup cannot be overwritten.
        fd = os.open(dest, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(fd)
        try:
            with store.connection() as src:
                out = sqlite3.connect(dest)
                try:
                    src.backup(out)
                finally:
                    out.close()
        except BaseException:
            dest.unlink(missing_ok=True)
            raise
        print(dest)
    else:
        if not 1 <= args.port <= 65535:
            raise Problem("شماره پورت معتبر نیست.")
        with store.connection() as db:
            if not db.execute("SELECT 1 FROM admin LIMIT 1").fetchone():
                raise Problem("ابتدا دستور init را اجرا کنید.")
        sys.path.insert(
            0, str(Path(__file__).resolve().parent / "vendor/waitress-3.0.2-py3-none-any.whl")
        )
        from waitress import serve

        app = Application(store, os.getenv("RADAR_PUBLIC_ORIGIN", ""))

        def tick():
            while True:
                try:
                    maintenance(store)
                    poll_mesh(store)
                except Exception:
                    logging.exception("Maintenance pass failed")
                time.sleep(20)

        threading.Thread(target=tick, name="radar-maintenance", daemon=True).start()
        logging.basicConfig(level=logging.INFO)
        serve(
            app,
            host="127.0.0.1",
            port=args.port,
            threads=6,
            channel_timeout=30,
            connection_limit=96,
            max_request_header_size=16384,
            max_request_body_size=1048576,
            expose_tracebacks=False,
        )


if __name__ == "__main__":
    try:
        main()
    except (Problem, ValueError, FileExistsError) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)

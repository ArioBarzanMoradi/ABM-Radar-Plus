#!/usr/bin/env python3
"""Configure an existing Nginx and certificate for a Jamshid subpath."""
import argparse
import os
from pathlib import Path
import re
import shutil
import subprocess

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--domain',required=True)
p.add_argument('--path',required=True,help='For example /jamshid/')
p.add_argument('--port',type=int,default=10443)
p.add_argument('--upstream-port',type=int,default=8788)
p.add_argument('--cert')
p.add_argument('--key')
a=p.parse_args()
if os.geteuid()!=0:p.error('Run with sudo.')
if not re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?',a.domain) or '..' in a.domain:p.error('Invalid domain.')
if not re.fullmatch(r'/(?:[A-Za-z0-9_-]+/)+',a.path):p.error('Use a path such as /jamshid/, ending in a slash.')
if not 1024<=a.port<=65535 or not 1024<=a.upstream_port<=65535:p.error('Use ports 1024..65535. The default preserves VPN port 443.')
if not shutil.which('nginx'):p.error('Install and configure Nginx first.')
cert=Path(a.cert or '/etc/letsencrypt/live/'+a.domain+'/fullchain.pem')
key=Path(a.key or '/etc/letsencrypt/live/'+a.domain+'/privkey.pem')
for f in (cert,key):
 if not f.is_file() or not re.fullmatch(r'/[A-Za-z0-9_./-]+',str(f)):p.error('Certificate/key file missing or invalid: '+str(f))
env=Path('/etc/radar-infra/panel.env')
if not env.is_file():p.error('Install the Jamshid panel first.')
subprocess.run(['nginx','-t'],check=True)
conf=Path('/etc/nginx/conf.d/jamshid-plus-web.conf')
old_conf=conf.read_bytes() if conf.exists() else None
old_env=env.read_bytes()
origin='https://'+a.domain+':'+str(a.port)
text='\n'.join(line for line in old_env.decode().splitlines() if not line.startswith('RADAR_PUBLIC_ORIGIN='))+'\nRADAR_PUBLIC_ORIGIN='+origin+'\n'
# Trailing slash on proxy_pass removes the public prefix before forwarding.
content=f'''# Managed by Jamshid Plus configure-web.py
server {{
    listen {a.port} ssl;
    listen [::]:{a.port} ssl;
    server_name {a.domain};
    ssl_certificate {cert};
    ssl_certificate_key {key};
    ssl_protocols TLSv1.2 TLSv1.3;
    client_max_body_size 256k;
    location = {a.path[:-1]} {{ return 308 {a.path}; }}
    location ^~ {a.path} {{
        proxy_pass http://127.0.0.1:{a.upstream_port}/;
        proxy_set_header Host $http_host;
        proxy_cookie_path / {a.path};
    }}
    location / {{ return 404; }}
}}
'''
try:
 conf.write_text(content)
 subprocess.run(['nginx','-t'],check=True)
 env.write_text(text)
 subprocess.run(['systemctl','restart','radar-infra.service'],check=True)
 subprocess.run(['systemctl','reload','nginx'],check=True)
except BaseException:
 env.write_bytes(old_env)
 if old_conf is None:conf.unlink(missing_ok=True)
 else:conf.write_bytes(old_conf)
 subprocess.run(['systemctl','restart','radar-infra.service'],check=False)
 subprocess.run(['nginx','-t'],check=False)
 subprocess.run(['systemctl','reload','nginx'],check=False)
 raise
print('Panel: '+origin+a.path)
print('Allow this TCP port in the host/provider firewall if needed: '+str(a.port))
print('Remote agents use the complete Panel URL above, including its web path.')

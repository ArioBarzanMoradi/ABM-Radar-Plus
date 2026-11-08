"""Read-only Linux observability using the standard library and iproute2."""
import ipaddress
import json
import os
from pathlib import Path
import platform
import re
import shutil
import socket
import struct
import subprocess
import time

VPN = re.compile(r"(wg-quick@|openvpn|xray|sing-box|hiddify|3x-ui|x-ui|hysteria|shadowsocks|ssserver|ocserv|strongswan|ipsec|charon|xl2tpd|tailscaled|zerotier|v2ray|trojan|outline|amnezia)", re.I)
HINTS = {22:"SSH",53:"DNS",80:"HTTP",443:"TLS / VPN احتمالی",500:"IPsec IKE احتمالی",1194:"OpenVPN احتمالی",1701:"L2TP احتمالی",1723:"PPTP احتمالی",4500:"IPsec NAT-T احتمالی",51820:"WireGuard احتمالی",8388:"Shadowsocks احتمالی"}

def output(args, timeout=2):
    try:
        p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,timeout=timeout,check=False)
        return p.stdout[:65536] if p.returncode==0 else ""
    except (OSError,subprocess.TimeoutExpired):
        return ""

def ip_json(args):
    try:
        value=json.loads(output(["ip","-j",*args]))
        return value if isinstance(value,list) else []
    except (ValueError,TypeError):
        return []

def local_ports():
    rows=[]
    for proto,state in (("TCP","0A"),("UDP","07")):
        for suffix in ("","6"):
            try: lines=Path("/proc/net/"+proto.lower()+suffix).read_text().splitlines()[1:]
            except OSError: continue
            for line in lines:
                c=line.split()
                if len(c)<4 or c[3]!=state:continue
                try:
                    raw,port=c[1].split(":")
                    b=bytes.fromhex(raw)
                    b=b[::-1] if not suffix else b"".join(b[i:i+4][::-1] for i in range(0,16,4))
                    address=socket.inet_ntop(socket.AF_INET6 if suffix else socket.AF_INET,b)
                    number=int(port,16)
                    ip=ipaddress.ip_address(address)
                except (ValueError,OSError):continue
                rows.append(dict(protocol=proto,number=number,address=address,family="IPv6" if suffix else "IPv4",scope="loopback" if ip.is_loopback else "all" if ip.is_unspecified else "address",hint=HINTS.get(number,"نامشخص")))
    return sorted(rows,key=lambda p:(p["number"],p["protocol"],p["family"],p["address"]))[:1000]

def counters():
    found={}
    try:
        for line in Path("/proc/net/dev").read_text().splitlines()[2:]:
            name,rest=line.split(":",1);n=rest.split()
            found[name.strip()]=(int(n[0]),int(n[8]))
    except (OSError,ValueError,IndexError):pass
    return found

def vpn_units(interfaces):
    rows=[]
    for line in output(["systemctl","list-units","--type=service","--all","--plain","--no-legend"],3).splitlines():
        parts=line.strip().lstrip("● ").split(None,4)
        if len(parts)>=4 and parts[0].endswith(".service") and VPN.search(parts[0]):
            rows.append(dict(name=parts[0][:150],state=parts[2][:30],substate=parts[3][:30]))
    for iface in interfaces:
        if iface["name"].startswith(("wg","tun","tap","tailscale","zt")):
            rows.append(dict(name=iface["name"],state="active" if iface["up"] else "inactive",substate="interface"))
    return rows[:80]

class SystemSampler:
    def __init__(self):
        self.previous=None
        self.previous_at=None

    def collect(self):
        now=time.monotonic();traffic=counters()
        routes={"ipv4":ip_json(["route","show","default"])[:8],"ipv6":ip_json(["-6","route","show","default"])[:8]}
        route_default=(routes["ipv4"] or routes["ipv6"] or [{}])[0].get("dev","")
        default=route_default or next((name for name in traffic if name!="lo"),"")
        interfaces=[]
        ip_interfaces={str(r.get("ifname","")):r for r in ip_json(["address","show"])}
        for name,(rx,tx) in list(traffic.items())[:64]:
            info=ip_interfaces.get(name,{})
            addresses=info.get("addr_info",[])[:32]
            try: up=bool(int(Path("/sys/class/net",name,"flags").read_text().strip(),16)&1)
            except (OSError,ValueError):up=False
            prev=self.previous.get(name) if self.previous else None
            dt=now-self.previous_at if self.previous_at is not None else 0
            rates=((rx-prev[0])/dt if rx>=prev[0] else None,(tx-prev[1])/dt if tx>=prev[1] else None) if prev and dt>0 else (None,None)
            interfaces.append(dict(name=name,up=up,default=name==route_default,rxBytes=rx,txBytes=tx,rxBps=round(rates[0],1) if rates[0] is not None else None,txBps=round(rates[1],1) if rates[1] is not None else None,ipv4=[str(a["local"]) for a in addresses if a.get("family")=="inet" and "local" in a],ipv6=[str(a["local"]) for a in addresses if a.get("family")=="inet6" and "local" in a]))
        self.previous=traffic;self.previous_at=now
        active=next((i for i in interfaces if i["name"]==default),{})
        try:
            dns=[l.split()[1] for l in Path("/etc/resolv.conf").read_text().splitlines() if l.strip().startswith("nameserver ")][:8]
        except OSError:dns=[]
        try: uptime=float(Path("/proc/uptime").read_text().split()[0])
        except (OSError,ValueError):uptime=None
        disk=shutil.disk_usage("/")
        return dict(hostname=socket.gethostname(),os=platform.system()+" "+platform.release(),uptime=uptime,load=list(os.getloadavg()),disk=dict(total=disk.total,used=disk.used,free=disk.free,percent=round(disk.used/disk.total*100,1)),network=dict(device=default,rxBps=active.get("rxBps"),txBps=active.get("txBps"),interfaces=interfaces,routes=routes,dns=dns),listeners=local_ports(),vpn=vpn_units(interfaces))

"""Validate the optional extended telemetry before storing it."""
import math
from .common import obj, items, string, host, portnum, one, Problem

def number(v, high=10**20):
    if v is None:return None
    if type(v) not in (int,float) or not math.isfinite(v) or not 0<=v<=high:raise Problem("مقدار اندازه‌گیری معتبر نیست.")
    return round(v,2)

def text(v,n=180):return string(v,n,False)
def probe(v):
    v=obj(v)
    if type(v.get("ok")) is not bool:raise Problem("نتیجهٔ پروب معتبر نیست.")
    return dict(ok=v["ok"],inconclusive=v.get("inconclusive") is True,summary=text(v.get("summary",v.get("detail","")),600),lines=[text(x,400) for x in items(v.get("lines",[]),24)],ms=number(v.get("ms"),120000))
def probes(value):
    if value is None:return None
    v=obj(value);checks={}
    for k,r in obj(v.get("checks",{})).items():
        if k in ("ipv4","ipv6","dns","https","icmp","stun"):checks[k]=probe(r)
    targets=[]
    for t in items(v.get("targets",[]),24):
        t=obj(t);targets.append(dict(host=host(t.get("host")),port=portnum(t.get("port")),name=text(t.get("name",""),100),tcp=probe(t.get("tcp")),icmp=probe(t.get("icmp"))))
    return dict(at=number(v.get("at")),checks=checks,targets=targets)
def system(value):
    if value is None:return None
    v=obj(value);d=obj(v.get("disk",{}));n=obj(v.get("network",{}))
    interfaces=[]
    for item in items(n.get("interfaces",[]),64):
        i=obj(item)
        interfaces.append(dict(name=text(i.get("name",""),64),up=i.get("up") is True,default=i.get("default") is True,rxBytes=number(i.get("rxBytes")),txBytes=number(i.get("txBytes")),rxBps=number(i.get("rxBps")),txBps=number(i.get("txBps")),ipv4=[text(x,100) for x in items(i.get("ipv4",[]),32)],ipv6=[text(x,100) for x in items(i.get("ipv6",[]),32)]))
    routes={}
    for family,values in obj(n.get("routes",{})).items():
        if family not in ("ipv4","ipv6"):continue
        routes[family]=[{k:text(str(val),150) for k,val in obj(r).items() if k in ("dst","gateway","dev","prefsrc","metric","protocol","scope")} for r in items(values,8)]
    listeners=[]
    for p in items(v.get("listeners",[]),1000):
        p=obj(p);listeners.append(dict(protocol=one(p.get("protocol"),{"TCP","UDP"}),number=portnum(p.get("number")),address=text(p.get("address",""),100),family=one(p.get("family"),{"IPv4","IPv6"}),scope=one(p.get("scope"),{"loopback","all","address"}),hint=text(p.get("hint",""),100)))
    vpn=[]
    for item in items(v.get("vpn",[]),80):
        item=obj(item);vpn.append(dict(name=text(item.get("name",""),150),state=text(item.get("state",""),30),substate=text(item.get("substate",""),30)))
    return dict(hostname=text(v.get("hostname","")),os=text(v.get("os","")),uptime=number(v.get("uptime")),load=[number(x) for x in items(v.get("load",[]),3)],disk={k:number(d.get(k),100 if k=="percent" else 10**20) for k in ("total","used","free","percent")},network=dict(device=text(n.get("device",""),64),rxBps=number(n.get("rxBps")),txBps=number(n.get("txBps")),interfaces=interfaces,routes=routes,dns=[text(x,100) for x in items(n.get("dns",[]),8)]),listeners=listeners,vpn=vpn)
def monitoring(value):
    v=obj(value)
    if type(v.get("protocolChecks")) is not bool:raise Problem("فعال‌بودن تست‌ها معتبر نیست.")
    targets=[]
    for t in items(v.get("targets",[]),24):
        t=obj(t);targets.append(dict(host=host(t.get("host")),port=portnum(t.get("port")),name=string(t.get("name",t.get("host")),100)))
    return dict(protocolChecks=v["protocolChecks"],targets=targets)


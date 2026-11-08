"""Fixed, bounded network checks. No shell strings, redirects or TLS bypass."""
import concurrent.futures
import http.client
import secrets
import socket
import ssl
import struct
import time

def result(ok, detail, started, unknown=False):
    return dict(ok=bool(ok),ms=round((time.monotonic()-started)*1000,1) if ok else None,detail=str(detail)[:250],inconclusive=bool(unknown))

def tcp(host,port=443,family=socket.AF_UNSPEC):
    start=time.monotonic()
    infos=socket.getaddrinfo(host,port,family,socket.SOCK_STREAM)
    for af,kind,proto,_,addr in infos[:8]:
        try:
            with socket.socket(af,kind,proto) as s:s.settimeout(1.5);s.connect(addr)
            return result(True,"TCP handshake برقرار شد",start)
        except OSError:pass
    return result(False,"اتصال TCP در این خانوادهٔ آدرس برقرار نشد",start)

def https(host,port=443,tls_only=False):
    start=time.monotonic()
    if tls_only:
        with socket.create_connection((host,port),timeout=3) as sock:
            with ssl.create_default_context().wrap_socket(sock,server_hostname=host) as secure:
                cert=secure.getpeercert()
                return result(True,"TLS معتبر · "+str(secure.version())+" · انقضا "+str(cert.get("notAfter","")),start)
    c=http.client.HTTPSConnection(host,port,timeout=3,context=ssl.create_default_context())
    try:
        c.request("GET","/",headers={"User-Agent":"ABM-Radar-Plus/2"})
        r=c.getresponse();r.read(512)
        return result(200<=r.status<400,"HTTPS پاسخ "+str(r.status),start)
    finally:c.close()

def stun(host,port=19302):
    start=time.monotonic();tx=secrets.token_bytes(12)
    addr=socket.getaddrinfo(host,port,socket.AF_UNSPEC,socket.SOCK_DGRAM)[0]
    with socket.socket(addr[0],socket.SOCK_DGRAM) as sock:
        sock.settimeout(3);sock.connect(addr[4]);sock.send(struct.pack("!HHI",1,0,0x2112a442)+tx);data=sock.recv(2048)
    valid=len(data)>=20 and data[:2]==b"\x01\x01" and data[4:8]==b"\x21\x12\xa4\x42" and data[8:20]==tx
    return result(valid,"پاسخ معتبر STUN" if valid else "پاسخ STUN نامعتبر",start,not valid)

def safe_call(fn,*args):
    started=time.monotonic()
    try:return fn(*args)
    except Exception as e:
        return result(False,"گواهی TLS تأیید نشد" if isinstance(e,ssl.SSLError) else "نام‌یابی، مسیر شبکه یا مهلت پاسخ ناموفق بود",started)

def collect(run_probe, targets, protocol_checks=False):
    # run_probe starts a bounded child, including a timeout around DNS resolution.
    tests=[]
    for target in targets[:24]:
        tests.append((target["host"],target["port"],target.get("name",target["host"])))
    checks={}
    if protocol_checks:
        fixed={"ipv4":dict(kind="ipv4",target="1.1.1.1",port=443),"ipv6":dict(kind="ipv6",target="2606:4700:4700::1111",port=443),"dns":dict(kind="dns",target="example.com"),"https":dict(kind="https",target="www.google.com",port=443),"icmp":dict(kind="ping",target="1.1.1.1"),"stun":dict(kind="stun",target="stun.l.google.com",port=19302)}
    else:fixed={}
    def probe_target(t):
        host,port,name=t
        return dict(host=host,port=port,name=name,tcp=run_probe(dict(kind="tcp",target=host,port=port)),icmp=run_probe(dict(kind="ping",target=host)))
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        globals_={k:pool.submit(run_probe,v) for k,v in fixed.items()}
        futures=[pool.submit(probe_target,t) for t in tests]
        for key,f in globals_.items():checks[key]=f.result()
        results=[f.result() for f in futures]
    return dict(at=int(time.time()*1000),checks=checks,targets=results)

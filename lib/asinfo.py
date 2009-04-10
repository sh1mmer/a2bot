
import os, socket

def _rev_ip(iptxt):
    try:
        l = iptxt.split('/')
        if len(l) > 1:
            n = { '8':1, '16':2, '24':3, '32':4 }[l[1]]
        else:
            n = 4
        ai = socket.getaddrinfo(l[0], 0)
        octs = ai[0][4][0].split('.')[:n]
    except:
        return None
    octs.reverse()
    return '.'.join(octs)

def _lookup(x):
    f = os.popen('host -t txt "%s.asn.cymru.com"' % x)
    buf = f.read()
    f.close()
    try:
        return buf.split('"')[1]
    except IndexError:
        return None

def origin(host):
    iptxt = _rev_ip(host)
    if iptxt:
        return _lookup('%s.origin' % iptxt)

def peer(host):
    iptxt = _rev_ip(host)
    if iptxt:
        return _lookup('%s.peer' % iptxt)

def desc(asn):
    try:
        asn = int(asn)
    except ValueError:
        return None
    return _lookup('AS%d' % asn)

if __name__ == '__main__':
    print origin('77.109.138.135')
    print origin('141.211.0.0/16')
    print peer('google.com')
    print peer('3303')
    print desc(42389)

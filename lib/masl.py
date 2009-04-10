
import re, urllib

__pat = re.compile(r'(?P<short_url>http://monkey.org/sl/[a-z0-9]+)</a>')

def shorten(url, desc):
    f = urllib.urlopen('http://monkey.org/cgi-bin/masl.cgi?%s' %
                       urllib.urlencode({ 'long_link':url, 'desc':desc }))
    buf = f.read()
    m = __pat.search(buf)
    if m:
        return m.group('short_url')
    return None

if __name__ == '__main__':
    print shorten('http://monkey.org', 'monkey')

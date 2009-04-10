
import csv, urllib
from xml.dom import minidom

APPID = 'gZoapAXV34FkztB4Db5yj5fb4ij7jfQsaUzajLvXx_GYYnVHKpvTq3dumcGrrw--'

def geocode(location):
    url = 'http://api.local.yahoo.com/MapsService/V1/geocode?' + \
          urllib.urlencode({'appid':APPID, 'location':location})
    buf = urllib.urlopen(url).read()
    dom = minidom.parseString(buf)
    d = {}
    for k in ('Address', 'City', 'State', 'Zip', 'Country',
              'Latitude', 'Longitude'):
        try:
            d[k] = dom.getElementsByTagName(k)[0].childNodes[0].data
        except IndexError:
            pass
    return d
            
WEATHER_URL = 'http://xml.weather.yahoo.com/forecastrss?p=%s'
WEATHER_NS = 'http://xml.weather.yahoo.com/ns/rss/1.0'

def weather(location):
    d = geocode(location)
    if 'Zip' not in d:
        return {}
    
    url = WEATHER_URL % d['Zip']
    buf = urllib.urlopen(url).read()
    dom = minidom.parseString(buf)
    forecasts = []
    try:
        ycondition = dom.getElementsByTagNameNS(WEATHER_NS, 'condition')[0]
    except IndexError:
        return {}
    for node in dom.getElementsByTagNameNS(WEATHER_NS, 'forecast'):
        forecasts.append({
            'date': node.getAttribute('date'),
            'low': node.getAttribute('low'),
            'high': node.getAttribute('high'),
            'condition': node.getAttribute('text')
        })
    return {
        'current_condition': ycondition.getAttribute('text'),
        'current_temp': ycondition.getAttribute('temp'),
        'forecasts': forecasts,
        'title': dom.getElementsByTagName('title')[0].firstChild.data
    }

def quote(sym):
    if isinstance(sym, str):
        sym = sym.split()
    url = 'http://finance.yahoo.com/d/quotes.csv?f=d1l1c1ohgv&s=%s' % '+'.join(sym)
    keys = ('date', 'price', 'change', 'open', 'high', 'low', 'volume')
    return [ dict(zip(keys, vals)) for vals in csv.reader(urllib.urlopen(url)) ]
    
if __name__ == '__main__':
    print quote('GOOG YHOO')
    print quote([ 'MSFT', 'CSCO' ])
    print weather('48105')
    print weather('SFO')
    print geocode('New York City') # XXX - no single Zip

# $Id$

try:
    import json
except ImportError:
    import simplejson as json

import urllib, urllib2

def translate(lang_from, lang_to, text):
    url = 'http://ajax.googleapis.com/ajax/services/language/translate?v=1.0&'
    if not lang_from or lang_from == 'auto':
        langpair = '|en'
    else:
        langpair = '%s|%s' % (lang_from, lang_to)
    query = urllib.urlencode({ 'q':text, 'langpair':langpair})
    req = urllib2.Request(url + query)
    req.add_header('Referer', 'http://10.0.9.51/translate')
    f = urllib2.urlopen(req)
    res = json.loads(f.read())
    if res['responseStatus'] == 200:
        return res['responseData']['translatedText']
    return ''

if __name__ == '__main__':
    import unaccent
    print translate('en', 'es', "why didn't that translate correctly?").translate(unaccent.unaccented_map()).encode('ascii', 'ignore')
    print translate(None, 'en', 'bonjour mes amis, comment allez-vous?')

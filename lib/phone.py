# $Id$

import re

import BeautifulSoup

import soundex, wiki

tag_re = re.compile("</?[a-z0-9A-Z]+.*?>|<!.*?-->", re.M|re.S)
ws_re = re.compile("[ \t\r\n]+")

def html2txt(s):
    # XXX
    s = s.replace('&nbsp;', '')
    s = s.replace('&#43;', '+')
    txt = tag_re.sub('', s)
    return ws_re.sub(' ', txt)

data = {}

def __add_record(name, d):
    idx = soundex.soundex(name)
    if idx in data:
        data[idx][d['Full Name']] = d
    else:
        data[idx] = { d['Full Name']: d }

def load_data():
    #soup = BeautifulSoup.BeautifulSoup(open('Employee+Directory.html'))
    w = wiki.WikiProxy()
    page = w.getPage('hr', 'Employee Directory')
    txt = w.renderContent('hr', page['id'],
                          page['content'].encode('ascii', 'ignore'),
                          { 'style':'clean' })
    soup = BeautifulSoup.BeautifulSoup(txt)
    
    tables = soup.findAll('table', { 'class':'confluenceTable' })

    for table in tables:
        colnames = [ x.string.strip() for x in table('tr')[0]('th') ]
        for row in table('tr')[1:]:
            d = dict(zip(colnames, [ html2txt(str(x)).strip()
                                     for x in row('td') ]))
            if 'Full Name' in d:
                for x in d['Full Name'].split():
                    __add_record(x, d)
            if 'Username' in d:
                __add_record(d['Username'], d)
            if 'E-mail' in d:
                __add_record(d['E-mail'].split('@')[0], d)

def lookup(name):
    if not data:
        load_data()
    name = name.lower()
    # Start with SOUNDEX match.
    idx = soundex.soundex(name)
    d = data.get(idx, {})
    l = []
    # Narrow to best match.
    for k, v in d.iteritems():
        for x in [ k, v.get('E-mail', ''), v.get('Username', '') ]:
            x = x.lower()
            if name in x:
                l.append(v)
                break
    # If no best match, return all.
    if not l:
        l = d.values()
    return l

if __name__ == '__main__':
    load_data()
    print lookup('dugong')

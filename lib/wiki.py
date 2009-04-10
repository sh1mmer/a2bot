# $Id$

import string, xmlrpclib
from wiki_keys import USERNAME, PASSWORD

all = string.maketrans('', '')
non_printable = all.translate(all, string.printable)

def asciify(txt):
    """Strip any non-printable ASCII chars."""
    return txt.translate(all, non_printable)

class WikiProxy(object):
    """http://confluence.atlassian.com/display/DOC/Remote+API+Specification
    """
    def __init__(self, url=URL, username=USERNAME, password=None):
        rpc = xmlrpclib.ServerProxy(url)
        self.api = rpc.confluence1
        self.username = username
        if password is None:
            password = PASSWORD.decode('base64')
        self.password = password
        self.login()

    def login(self):
        self.token = self.api.login(self.username, self.password)
        
    def __getattr__(self, name):
        def method(*args, **kwargs):
            return getattr(self.api, name)(self.token, *args, **kwargs)
        return method

if __name__ == '__main__':
    wiki = WikiProxy('https://wiki.zattoo.com/rpc/xmlrpc')
    page = wiki.getPage('hr', 'Employee Directory')
    #print page['content'].encode('ascii', 'ignore')
    print wiki.renderContent('hr', page['id'],
                             page['content'].encode('ascii', 'ignore'),
                             { 'style':'clean' })

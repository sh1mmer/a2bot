# $Id$

import os, sys, time
import wiki

class Logger(object):
    """Irssi-compatible logger, with scheduled daily uploads to the wiki."""
    
    def __init__(self, logdir, timeout_fn=None):
        self.logdir = logdir
        self.channels = {}
        self.timeout_fn = timeout_fn
        if timeout_fn:
            self.schedule_timeout()

    def schedule_timeout(self):
        # Schedule uploads at midnight, daily
        l = list(time.localtime())
        l[2] += 1
        l[3] = l[4] = 0
        l[5] = 2 # XXX
        utc = time.mktime(l)
        print '[wikilog] scheduling next log rotation for %s' % time.ctime(utc)
        self.timeout_fn(utc, self.rotate)

    def join(self, channel):
        filename = os.path.join(self.logdir, '%s_%s' %
                                (channel, time.strftime('%m-%d-%Y')))
        f = self.channels[channel] = open(filename, 'a', 1)
        #f.write('--- Log opened %s\n' % time.ctime())

    def leave(self, channel):
        try:
            f = self.channels.pop(channel)
            #f.write('--- Log closed %s\n' % time.ctime())
            f.close()
        except KeyError:
            pass
    
    def log_event(self, event):
        if event.dst in self.channels:
            f = self.channels[event.dst]
            etype = event.eventtype()
            t = time.localtime(event.ts)
            ts = '%02d:%02d' % (t[3], t[4])

            if etype == 'pubmsg':
                f.write('%s <%s> %s\n' % (ts, event.src, event.msg))
            elif etype == 'action':
                f.write('%s  * %s %s\n' % (ts, event.src, event.msg))
            elif etype == 'join':
                # XXX - ignore my own joins
                if event.src != event.mynick:
                    f.write('%s -!- %s [%s] has joined %s\n' %
                            (ts, event.src, event.hostmask, event.dst))
            elif etype == 'part':
                f.write('%s -!- %s [%s] has left %s [%s]\n' %
                        (ts, event.src, event.hostmask, event.dst, event.msg))
            elif etype == 'quit':
                f.write('%s -!- %s [%s] has quit [%s]\n' %
                        (ts, event.src, event.hostmask, event.msg))
            #print ('type: %s src: %r source: %r dst: %r msg: %r args: %r' % 
            #       (etype, event.src, event.source(), event.dst,
            #        event.msg, event.arguments()))

    def lastlog(self, channel, count):
        """Return list of last <count> lines on <channel>."""
        try:
            count = int(count)
            f = os.popen('egrep -v "\-\!\-" %s | tail -n %s' % (self.channels[channel].name, count))
            l = f.readlines()
            f.close()
            return [ x.strip() for x in l ]
        except:
            return []

    def rotate(self):
        # Open new logfiles
        for chan in self.channels.keys():
            print '[wikilog] reopening', chan
            self.join(chan)
        # Reschedule ourselves
        if self.timeout_fn:
            self.schedule_timeout()
        
    def upload(self):
        if os.fork() == 0:
            # Double-fork to prevent SIGCHLD
            if os.fork():
                sys.exit(0)
            # Upload everything in log directory to the wiki
            s = wiki.WikiProxy()
            for name in os.listdir(self.logdir):
                filename = os.path.join(self.logdir, name)
                buf = wiki.asciify(open(filename).read())
                if buf:
                    # Sanitize page name
                    name = name.replace('#', '')
                    pname = name.split('_', 1)[0]
                    try:
                        parent = s.getPage('irc', pname) 
                    except wiki.xmlrpclib.Fault:
                        parent = s.storePage({
                            'space':'irc',
                            'title':pname,
                            'content':'' })
                    print '[wikilog] storing %s' % name
                    ret = s.storePage({
                        'space':parent['space'],
                        'parentId':parent['id'],
                        'title':name,
                        'content':buf })
                    if 'id' in ret:
                        os.unlink(filename)
                else:
                    os.unlink(filename)
            sys.exit(0)
        # Child exits (forking a grandchild) immediately
        os.wait()
        # XXX
        time.sleep(2)
        # Open new logfiles
        for chan in self.channels.keys():
            print '[wikilog] reopening', chan
            self.join(chan)
        # Reschedule ourselves
        if self.timeout_fn:
            self.schedule_timeout()

    def close(self):
        for chan in self.channels.keys():
            self.leave(chan)

if __name__ == '__main__':
    w = Logger('logtmp')
    w.upload()

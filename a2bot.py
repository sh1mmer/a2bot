#!/usr/bin/env python

# $Id$

# stdlib
import cPickle as pickle, os, random, re, socket, sys, time, traceback, urllib, struct

# third-party
import GeoIP
from lib import ircbot, irclib

# local
from lib import asinfo, dialect, masl, phone, translate, unaccent, wikilog, yahoo

decorator_with_args = lambda decorator: lambda *args, **kwargs: lambda func: decorator(func, *args, **kwargs)

@decorator_with_args
def assign(f, l, pat):
    l.append((re.compile(pat), f))
    return f

class A2bot(ircbot.SingleServerIRCBot):
    __version__ = 'A2bot 0.1'
    datadir = 'data'
    logdir = 'irclogs'
    #logurl = 'http://irc.zattoo.com/logs/?channel='
    commands = []

    greetings = ('aloha', 'ciao', 'gruezi', 'hallo', 'hello', 'hey',
                 'heya', 'hi', 'hi there', 'hiya', 'hoi', 'hola', 'howdy',
                 'que pasa', 'namaste', 'ni hao', 'privyet', 'salut', 'shalom',
                 'sup', "what's up", 'wie gehts', 'wud up', 'yo', 'zdravo')
    goodbyes = ('adios', 'a bientot', 'au revoir', 'bis spaeter', 'bye',
                'ciao', 'cu', 'cya', 'goodbye', 'later', 'l8r', 'night',
                'nite', 'sayonara', 'servus', 'tschau', 'widerluege',
                'zai jian')
    thanks = ('arigato', 'awesome', 'cheers', 'danke schon', 'good', 'gracias',
              'grazie', 'hvala', 'kewl', 'mahalo', 'merci', 'thanks',
              'thank you', 'werd', 'w00t', 'xiexie', 'you rock')
    skipfacts = dict.fromkeys(('and', 'but', 'how', 'it', 'that', 'there',
                               'this', 'who', 'what', 'where', 'when', 'why',
                               'which', 'you', 'he', 'she', 'they', 'we'))
    
    def __init__(self, servers, nickname, realname):
        ircbot.SingleServerIRCBot.__init__(self, servers, nickname, realname,
                                           reconnection_interval=3)
        self.db = { 'channels': {}, 'karma': {}, 'knowledge': {}, 'seen': {} }
        if not os.path.exists(self.datadir):
            os.makedirs(self.datadir)
        # Reload our db
        for name in self.db:
            try:
                f = open('%s/%s.pkl' % (self.datadir, name))
                self.db[name] = pickle.load(f)
            except IOError:
                pass
        # Load text databases
        f = open('%s/excuses.txt' % self.datadir)
        self.excuses = [ x.strip() for x in f.readlines() ]
        f = open('%s/yow.lines' % self.datadir)
        self.yow = [ x.strip().replace('\n', '')
                     for x in f.read().split('\x00')[1:] if x ]
        f = open('%s/blootbot.lart' % self.datadir)
        self.lart = [ x.strip() for x in f ]
        f = open('%s/deepthoughts.txt' % self.datadir)
        self.thoughts = [ x.strip() for x in f ]
        f = open('%s/zipcodes.txt' % self.datadir)
        self.zipcodes = dict([ x.strip().split(':', 1) for x in f ])
        f = open('%s/areacodes.supyfact' % self.datadir)
        self.areacodes = dict([ x.strip().split(':', 1) for x in f ])
        f = open('%s/punnish.txt' % self.datadir)
        self.punnish = [ x.strip() for x in f ]

        # Open geoip handle
        self.geoip = GeoIP.open('%s/GeoLiteCity.dat' % self.datadir,
                                GeoIP.GEOIP_MEMORY_CACHE)
        # Setup unaccented map
        self.umap = unaccent.unaccented_map()
        
        # Setup wiki logging
        if not os.path.exists(self.logdir):
            os.makedirs(self.logdir)
        self.logger = wikilog.Logger(self.logdir, self.timeout)
    
    def reply(self, conn, event, msg):
        if event.dst != event.mynick:
            conn.privmsg(event.dst, msg)
            # Log our own responses
            e = irclib.Event('pubmsg', event.mynick, event.dst, [msg])
            self.decorate_event(conn, e)
            self.logger.log_event(e)
        else:
            conn.privmsg(event.src, msg)

    def notice(self, conn, event, msg):
        if event.dst != event.mynick:
            conn.notice(event.dst, msg)
        else:
            conn.notice(event.src, msg)

    def action(self, conn, event, msg):
        if event.dst == event.mynick:
            conn.action(event.src, msg)
        else:
            conn.action(event.dst, msg)

    def timeout(self, ts, callback, *args):
        self.ircobj.execute_at(ts, callback, arguments=args)

    @assign(commands, r'^help$')
    def cmd_help(self, conn, event, match):
        if event.dst == event.mynick:
            conn.notice(event.src, '*** a2bot help ***')
            for pat, func in self.commands:
                if func.__doc__ is not None:
                    conn.notice(event.src, func.__doc__)
    
    @assign(commands, r'^greet (?P<nick>[\S]+) on (?P<chan>#[\S]+)')
    def cmd_greet(self, conn, event, match):
        """greet <nick> on #<channel> -- say hello"""
        conn.privmsg(match.group('chan'), '%s %s' %
                     (random.choice(self.greetings), match.group('nick')))
    
    @assign(commands, r'^botsnack')
    def cmd_botsnack(self, conn, event, match):
        """botsnack -- feed the bot"""
        self.reply(conn, event, '%s, %s!' %
                   (random.choice(self.thanks), event.src))

    @assign(commands, r'^excuse[s]?[?]?')
    def cmd_excuse(self, conn, event, match):
        """excuse -- come up with a plausible excuse"""
        self.reply(conn, event, random.choice(self.excuses))

    #@assign(commands, r'^update$')
    def cmd_reload(self, conn, event, match):
        if event.dst == event.mynick:
            #f = os.popen('svn up')
            #self.reply(conn, event, '|'.join(f.readlines()))
            self.shutdown()
    
    @assign(commands, r'^yow')
    def cmd_yow(self, conn, event, match):
        """yow -- Zippy the Pinhead quote"""
        self.reply(conn, event, random.choice(self.yow))

    @assign(commands, r'^dialect (?P<lang>chef|fudd|olde)[:]?(?P<msg>.*)')
    def cmd_dialect(self, conn, event, match):
        """dialect chef|fudd|olde <msg> -- translate into a dialect"""
        self.reply(conn, event,
                   dialect.translate(match.group('msg').strip(),
                                     match.group('lang')))
    
    @assign(commands, r'^translate (?P<from>[a-z][a-z])2(?P<to>[a-z][a-z])[:]?(?P<msg>.*)$')
    @assign(commands, r'^translate (?P<from>)(?P<to>)(?P<msg>.*)$')
    def cmd_translate(self, conn, event, match):
        """translate [<lang>2<lang>:] <msg> -- translate between languages"""
        msg = match.group('msg').strip()
        fl, tl = match.group('from'), match.group('to')
        if fl == '': fl = 'auto'
        if tl == '': tl = 'en'
        if msg.startswith('http'):
            url = 'http://google.com/translate?' + \
                  urllib.urlencode({ 'u':msg, 'sl':fl, 'tl':tl })
            desc = 'translation posted by %s to %s on %s' % \
                   (event.src, event.dst, time.ctime())
            self.reply(conn, event, masl.shorten(url, desc))
        else:
            txt = translate.translate(fl, tl, msg)
            if txt:
                txt = txt.translate(self.umap).encode('ascii', 'ignore')
                self.reply(conn, event, txt)
            else:
                self.reply(conn, event, 'sorry %s, i dunno' % event.src)

    @assign(commands, r'^geoip (?P<ip>[\S]+)[ ?]*$')
    def cmd_geoip(self, conn, event, match):
        try:
            ip = socket.gethostbyname(match.group('ip'))
            self.reply(conn, event, match.group('ip') + ": " +
                       str(self.geoip.record_by_addr(ip)))
        except socket.gaierror:
            self.reply(conn, event, 'bad hostname')
        except SystemError:
            self.reply(conn, event, 'no record for %s' % ip)

    @assign(commands, r'^(as|AS)([nN])?[ ]*(?P<asn>[\d]+)[?]?$')
    def cmd_asinfo(self, conn, event, match):
        """asn <num> -- lookup description for ASN <num>"""
        x = asinfo.desc(match.group('asn'))
        self.reply(conn, event, x)

    @assign(commands, r'^(as|AS)[ ]*peer[s]? (?P<host>[\S]+)[?]?$')
    def cmd_aspeer(self, conn, event, match):
        """as peer <host|prefix> -- lookup BGP peer ASNs for <host|prefix>"""
        x = asinfo.peer(match.group('host'))
        if x:
            self.reply(conn, event, x)
        else:
            self.reply(conn, event, 'bad host/prefix: %r' %
                       match.group('host'))

    @assign(commands, r'^(as|AS)[ ]*origin (?P<host>[\S]+)[?]?$')
    def cmd_asorigin(self, conn, event, match):
        """as origin <host|prefix> -- lookup BGP origin ASN for <host|prefix>"""
        x = asinfo.origin(match.group('host'))
        if x:
            self.reply(conn, event, x)
        else:
            self.reply(conn, event, 'bad host/prefix: %r' %
                       match.group('host'))

    @assign(commands, r'^quote (?P<sym>[ A-Z]+)')
    def cmd_quote(self, conn, event, match):
        """quote <symbol> -- lookup current stock information"""
        l = match.group('sym').split()
        for x, y in zip(l, yahoo.quote(l)):
            self.reply(conn, event, '%s: %r' % (x, y))
    
    @assign(commands, r'^weather (?P<where>[0-9A-Za-z]+)[?]?$')
    def cmd_weather(self, conn, event, match):
        """weather <zip|airport_code> -- report US weather forecast"""
        d = yahoo.weather(match.group('where'))
        if d:
            l = [ '%s | Today: %s %s' % (d['title'].split(' - ')[-1],
                                          d['current_condition'],
                                          d['current_temp']) ]
            for f in d['forecasts']:
                l.append('%s: %s %s/%s' % (f['date'], f['condition'],
                                         f['high'], f['low']))
            self.reply(conn, event, ' | '.join(l))
        else:
            self.reply(conn, event, 'sorry %s, dunno %r' %
                       (event.src, match.group('where')))
    
    @assign(commands, r'^join (?P<chan>#[\S]+)')
    def cmd_join(self, conn, event, match):
        """join #<channel> -- start monitoring a channel"""
        if event.dst == event.mynick and event.src == 'dugsong':
            chan = match.group('chan')
            conn.join(chan)
            conn.mode(chan, '-t')
            self.logger.join(chan)
            self.db['channels'][chan] = 1
            self.reply(conn, event, 'ok, %s' % event.src)
    
    @assign(commands, r'^leave (?P<chan>#[\S]+)')
    def cmd_leave(self, conn, event, match):
        """leave #<channel> -- stop monitoring a channel"""
        if event.dst == event.mynick and event.src == 'dugsong':
            chan = match.group('chan')
            conn.part(chan)
            self.logger.leave(chan)
            self.reply(conn, event, 'ok, %s' % event.src)
            try:
                del self.db['channels'][chan]
            except KeyError:
                pass

    #@assign(commands, r'^phone (?P<name>[@ \w]+)[?]?')
    def cmd_phone(self, conn, event, match):
        """phone <name> -- lookup employee info"""
        name = match.group('name')
        l = phone.lookup(name)
        for d in l:
            l = [ d['Full Name'], d['Title'], d['Location'] ]
            for k in ('E-mail', 'Username', 'Skype ID', 'SkypeID',
                      'Mobile Phone', 'Mobile', 'Telephone'):
                if d.get(k):
                    l.append('%s: %s' % (k, d[k]))
            self.reply(conn, event, ' | '.join(l))
        if not l:
            self.reply(conn, event, 'no record for %r' % name)
   
    @assign(commands, r'^seen (?P<nick>[\S]+)[?]?')
    def cmd_seen(self, conn, event, match):
        """seen <nick> -- report last time seen"""
        nick = match.group('nick')
        if nick == event.src:
            self.reply(conn, event, 'what are you, a vampire?')
        elif nick == event.mynick:
            self.reply(conn, event, 'last time i looked in the mirror!')
        else:
            t = self.db['seen'].get(nick, 0)
            if t:
                self.reply(conn, event, '%s was last seen %s, saying %r' %
                           (nick, time.ctime(t[0]), t[1]))
            else:
                self.reply(conn, event, 'never seen %s' % nick)

    @assign(commands, r'^lastlog (?P<cnt>[\d]+)[ ]*(?P<chan>#[\S]+)?$')
    def cmd_lastlog(self, conn, event, match):
        """lastlog <count> [#<channel>] -- report last lines on a channel"""
        if isinstance(match, tuple):
            cnt, chan = match
        else:
            cnt = min(int(match.group('cnt')), 8)
            chan = match.group('chan') or event.dst
        
        lines = self.logger.lastlog(chan, cnt)
        if lines:
            conn.notice(event.src, '*** last %d lines on %s ***' % (cnt, chan))
            for line in lines:
                conn.notice(event.src, line)
            #conn.notice(event.src, '*** for more visit %s%s' %
            #            (self.logurl, urllib.quote(chan)))
        else:
            conn.notice(event.src, '*** no lastlog for %s ***' % chan)

    @assign(commands, r'^status$')
    def cmd_stats(self, conn, event, match):
        """status -- print bot status"""
        self.reply(conn, event, 'channels monitored: %s' %
                   ' '.join(self.db['channels'].keys()))
        self.reply(conn, event, 'facts learned: %s' %
                   len(self.db['knowledge']))
        
    @assign(commands, r'^forget (?P<thing>[ \S]+)$')
    def cmd_forget(self, conn, event, match):
        """forget <x> -- forget something"""
        x = match.group('thing').strip()
        print '[forget] %r' % x
        self.db['knowledge'].pop(x, None)
        self.reply(conn, event, 'ok, %s, forgot %r' % (event.src, x))
        
    @assign(commands, r'^karma (?P<nick>[\S]+)')
    def cmd_karma(self, conn, event, match):
        """karma <nick> -- report karma"""
        nick = match.group('nick')
        msg = 'karma for %s: %d' % (nick, self.db['karma'].get(nick, 0))
        self.reply(conn, event, msg)
    
    @assign(commands, r'[\S]+\+\+')
    def cmd_rocks(self, conn, event, match):
        """<nick>++ -- increment karma"""
        if event.dst == event.mynick:
            self.reply(conn, event, 'karma must be given in public!')
        else:
            for m in re.findall('[\S]+\+\+', event.msg):
                nick = m[:-2]
                if event.src == nick:
                    self.reply(conn, event, 'no ego-masturbation, %s' %
                               event.src)
                else:
                    self.db['karma'][nick] = self.db['karma'].get(nick, 0) + 1
    
    @assign(commands, r'[\S]+\-\-')
    def cmd_sucks(self, conn, event, match):
        """<nick>-- -- decrement karma"""
        if event.dst == event.mynick:
            self.reply(conn, event, 'karma must be docked in public!')
        else:
            for m in re.findall('[\S]+\-\-', event.msg):
                nick = m[:-2]
                if event.src == nick:
                    self.reply(conn, event, "don't worry, be happy %s" %
                               event.src)
                else:
                    self.db['karma'][nick] = self.db['karma'].get(nick, 0) - 1

    @assign(commands, r"""^(%s)(.* a2bot)?[?!]*$""" % '|'.join(greetings))
    def cmd_hello(self, conn, event, match):
        self.reply(conn, event, '%s %s' %
                   (random.choice(self.greetings), event.src))

    @assign(commands, r'^(%s)(.* a2bot)?[.!]*$' % '|'.join(goodbyes))
    def cmd_goodbye(self, conn, event, match):
        self.reply(conn, event, '%s %s' % 
                   (random.choice(self.goodbyes), event.src))
    
    @assign(commands, r'^(%s)(.* a2bot)' % '|'.join(thanks))
    def cmd_thanks(self, conn, event, match):
        self.reply(conn, event, "you're welcome, %s" % event.src)

    @assign(commands, r'^(is (a )?)?(bad|crazy|die|dumb|fu[c]?k (yo)?u|go away|lame[s]?|moron|shut[ ]?up|stupid|(yo)?u su[c]?k|sux|wtf)')
    def cmd_insult(self, conn, event, match):
        if event.mynick in event.msg:
            self.action(conn, event,
                        random.choice(self.lart).replace('WHO', event.src))
    
    @assign(commands, r'^lart (?P<nick>[\S]+)')
    def cmd_lart(self, conn, event, match):
        """lart <nick> -- Luser Attitude Readjustment Tool"""
        nick = match.group('nick')
        if nick == event.mynick:
            nick = event.src
        elif nick == "itself":
            nick = event.src
        self.action(conn, event, random.choice(self.lart).replace('WHO', nick))

    @assign(commands, r'^punnish (?P<nick>[\S]+)')
    def cmd_punnish(self, conn, event, match):
        """punnish <nick> -- punitive retaliation for being punny"""
        nick = match.group('nick')
        if nick == event.mynick:
            nick = event.src
        elif nick == "itself":
            nick = event.src
        self.action(conn, event, random.choice(self.punnish).replace('WHO', nick))

    @assign(commands, r'^area(code)? (?P<num>[\d]+)')
    def cmd_area(self, conn, event, match):
        num = match.group('num')
        self.reply(conn, event,
                   self.areacodes.get(num, 'no idea, %s' % event.src))

    @assign(commands, r'^zip(code)? (?P<num>[\d]+)')
    def cmd_zip(self, conn, event, match):
        num = match.group('num')
        self.reply(conn, event,
                   self.zipcodes.get(num, 'no idea, %s' % event.src))
    
    @assign(commands, r'^inet_ntoa (?P<ipnum>[\d]+)')
    def cmd_inet_ntoa(self, conn, event, match):
        ipnum = match.group('ipnum')
        self.reply(conn, event, socket.inet_ntoa(struct.pack("I", int(ipnum))))
        
    @assign(commands, r'^deepthought')
    def cmd_deepthought(self, conn, event, match):
        self.reply(conn, event, random.choice(self.thoughts))

    @assign(commands, r'([(])?(?P<url>http[s]?://[\S]+)(?(1)[)])')
    def def_masl(self, conn, event, match):
        if event.dst != event.mynick:
            url = match.group('url')
            if len(url) >= 50:
                desc = 'posted by %s to %s on %s' % \
                       (event.src, event.dst, time.ctime())
                self.reply(conn, event, masl.shorten(url, desc))
    
    @assign(commands, r"^([yo]*u are|you're|ur) (?P<thing>[ \S]+)")
    @assign(commands, r'^(is|iz) (?P<thing>[ \S]+)')
    def cmd_reflect(self, conn, event, match):
        if event.msg.startswith(event.mynick):
            self.reply(conn, event, "no, %s, you're %s!" %
                       (event.src, match.group('thing')))
    
    @assign(commands, r"(?P<x>[ \S]+) (is|are) (?P<y>[^\?]+)$")
    @assign(commands, r"^(?P<x>[ \S]+)[=]+(?P<y>[ \S]+)$")
    @assign(commands, r"^(?P<x>(?!(who|what|where|when|why|how|he|she|it|them)).*)'s (?P<y>[^\?]+)$")
    def cmd_learn(self, conn, event, match):
        """<x> is|are <y> -- teach something"""
        x = match.group('x').strip()
        y = match.group('y').strip()
        if len(x.split()) < 3 and x not in self.skipfacts:
            print '[learn] %r = %r' % (x, y)
            self.db['knowledge'][x] = y
            if event.dst == event.mynick:
                self.reply(conn, event, 'ok %s, %s' %
                           (event.src, match.group(0)))

    @assign(commands, r'((who|what|where|when|why|how) (is|are) )?(?P<thing>[ \S]+)\?$')
    @assign(commands, r'^(?P<thing>(?:\S+\s+)?[^\s!?.]+)[!?.]*$')
    def cmd_answer(self, conn, event, match):
        """[who|what is|are] <x>? -- ask something"""
        x = match.group('thing')
        y = self.db['knowledge'].get(x)
        if y is not None:
            if y.lower().startswith('<reply>'):
                y = random.choice(y[7:].strip().split('|'))
                self.reply(conn, event, y)
            elif y.lower().startswith('<action>'):
                y = random.choice(y[8:].strip().split('|'))
                if event.dst == event.mynick:
                    conn.action(event.src, y)
                else:
                    conn.action(event.dst, y)
            else:
                y = random.choice(y.strip().split('|'))
                if x.endswith('s'):
                    self.reply(conn, event, '%s are %s' % (x, y))
                else:
                    self.reply(conn, event, '%s is %s' % (x, y))
        elif event.msg.startswith(event.mynick):
            # XXX
            if event.msg.endswith('?') or \
                   match.group(0).split(None, 1)[0] in self.skipfacts:
                self.reply(conn, event, 'i dunno, %s' % event.src)
    
    def get_version(self):
        return self.__version__
    
    def dispatch_event(self, conn, event):
        # XXX - handle direct address
        if event.msg.startswith(event.mynick):
            msg = event.msg.split(None, 1)[-1]
        else:
            msg = event.msg
        for pat, func in self.commands:
            m = pat.search(msg)
            if m is not None:
                print >>sys.stderr, '[debug] %s > %s: %r ==> %s' % \
                      (event.src, event.dst, event.msg, func.func_name)
                try:
                    func(self, conn, event, m)
                except Exception, e:
                    if isinstance(e, SystemExit):
                        raise
                    exc_type, _, tb = sys.exc_info()
                    filename, line, funcname, _ = traceback.extract_tb(tb, 1)[0]
                    del tb
                    errmsg = "Uncaught %s at %s:%d in %s: %s" % \
                        (exc_type.__name__, filename, line, funcname, e)
                    self.notice(conn, event, errmsg)
                    traceback.print_exc()
                break
    
    def decorate_event(self, conn, event):
        event.ts = time.time()
        l = event.source().split('!')
        event.src = l[0]
        event.hostmask = l[-1]
        event.dst = event.target()
        event.msg = ' '.join(event.arguments())
        event.mynick = conn.get_nickname()
        event.targeted = event.msg.startswith(event.mynick)
    
    def on_welcome(self, conn, event):
        """Server join handler."""
        # Restore channel joins
        for chan in self.db['channels']:
            conn.join(chan)
            conn.mode(chan, '-t')
            self.logger.join(chan)
    
    def on_privmsg(self, conn, event):
        """PRIVMSG handler."""
        self.decorate_event(conn, event)
        event.targeted = True
        self.dispatch_event(conn, event)
        
    def on_pubmsg(self, conn, event):
        """PUBMSG handler."""
        self.decorate_event(conn, event)
        # Track seen only for public msgs
        self.db['seen'][event.src] = (event.ts, event.msg)
        # Log event
        self.logger.log_event(event)
        self.dispatch_event(conn, event)

    def on_join(self, conn, event):
        """JOIN handler."""
        self.decorate_event(conn, event)
        if event.src != event.mynick:
            self.logger.log_event(event)
            # Each new channel member gets the lastlog
            self.cmd_lastlog(conn, event, (3, event.dst))

    def _on_xxx(self, conn, event):
        """Catch-all handler."""
        self.decorate_event(conn, event)
        self.logger.log_event(event)

    on_action = on_part = on_quit = _on_xxx
    
    def shutdown(self):
        # Close logs
        self.logger.close()
        
        # Save db on shutdown
        for name, db in self.db.iteritems():
            print '[shutdown] saving %s]' % name
            f = open('%s/%s.pkl' % (self.datadir, name), 'w')
            pickle.dump(db, f)
            f.close()
        sys.exit(0)

if __name__ == '__main__':
    hostname = sys.argv[1]
    port = 6667
    if ':' in hostname:
        hostname, port = hostname.split(':', 1)
        port = int(port)
    servers = [ (hostname, port) ]
    a2bot = A2bot(servers, 'a2bot', '/msg a2bot help')
    try:
        a2bot.start()
    except KeyboardInterrupt:
        a2bot.shutdown()
    

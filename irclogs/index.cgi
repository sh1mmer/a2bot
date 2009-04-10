#!/usr/bin/env python

import cgi, re, time

def main():
    form = cgi.FieldStorage()
    channel = form.getfirst('channel') or '#dev'
    date = form.getfirst('date') or time.strftime('%m/%d/%Y')
    filename = channel + '_' + date.replace('/', '-')
    
    print """Content-type: text/html

<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN"
                    "http://www.w3.org/TR/html4/loose.dtd">
<html>
<head>
<title>Zattoo IRC logs</title>
<link rel="stylesheet" href="index.css" type="text/css">
<link rel="stylesheet" href="http://dev.jquery.com/view/tags/ui/latest/themes/flora/flora.datepicker.css" type="text/css">
<script src="http://code.jquery.com/jquery-latest.js"></script>
<script>
$(document).ready(function(){
  $('#date').datepicker();
});
</script>
</head>
<body>
<script src="http://dev.jquery.com/view/tags/ui/latest/ui/ui.datepicker.js"></script>
<form id="mainForm" target="/logs/">
channel: <input type="text" id="channel" name="channel" value="%s" size="12" />
date: <input type="text" id="date" name="date" value="%s" size="12" onchange="$('#mainForm').submit()"/>
<input type="submit" value="submit" />
</form>
<p />
""" % (channel, date)

    urlpat = re.compile(r'([(])?(?P<url>http[s]?://[\S]+)(?(1)[)])')
    def _hyperlink(match):
        url = match.group('url')
        txt = '<a href="%s">%s</a>' % (url, url)
        if match.group(1):
            txt = '(%s)' % txt
        return txt
    
    try:
        for line in open(filename):
            line = cgi.escape(line)
            l = line.split(None, 1)
            if len(l) != 2:
                continue
            ts, msg = l
            # XXX - URL hyperlinking
            msg = re.sub(urlpat, _hyperlink, msg)
            # XXX - irssi highlighting
            if msg.startswith('*'):
                mt = 'me'
            elif msg.startswith('-!-'):
                mt = 'nt'
            else:
                mt = 'nm'
            print '<span class="tm"><a href="#%s" name="%s">%s</a></span> <span class="%s">%s</span><br />' % (ts, ts, ts, mt, msg)
    except IOError:
        print 'No logfile found:', filename
    
    print """<p>
<span class="dl">[<a href="%s">Download</a>]</span>
</p>
</body></html>""" % (filename.replace('#', '%23'), )

if __name__ == '__main__':
    main()

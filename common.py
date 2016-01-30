import csv
import datetime
import json
import math
import os
import os.path
import re
import sys
from urllib2 import urlopen
from xml.dom.minidom import parse, parseString

leaderboards_url = 'http://steamcommunity.com/stats/247080/leaderboards/?xml=1'
api_key = file('apikey.txt', 'r').read().strip()

# day/month/year
# example: 7/10/2015
daily_re = re.compile('([0-9]+)/([0-9]+)/([0-9]{4})_PROD')

# https://twitter.com/Mendayen/status/687039791234465793
invalid_char_re = re.compile(ur'[^\x09\x0A\x0D\x20-\uD7FF\uE000-\uFFFD\u10000-\u10FFFF]')
assert not invalid_char_re.match('y')

# -> [(datetime.date, url string)]
class Leaderboards(object):
    CADENCE_SPEED = 'http://steamcommunity.com/stats/247080/leaderboards/740000/?xml=1'
    DORIAN_SPEED = 'http://steamcommunity.com/stats/247080/leaderboards/741116/?xml=1'
    DOVE_SPEED = 'http://steamcommunity.com/stats/247080/leaderboards/741329/?xml=1'

    def __init__(self):
        f = urlopen(leaderboards_url)
        text = f.read()

        # Work around invalid characters in the XML.
        text = unicode(text, 'utf-8', 'ignore')
        text = invalid_char_re.sub('', text)

        self.dom = parseString(text)

    def query_dailies(self):
        name_nodes = self.dom.getElementsByTagName('name')
        dailies = []
        for name_node in name_nodes:
            for child in name_node.childNodes:
                if child.nodeType == child.CDATA_SECTION_NODE:
                    cdata = child.data
                    name = cdata.strip()
                    m = daily_re.match(name)
                    if m:
                        when = datetime.date(
                            int(m.group(3)),
                            int(m.group(2)),
                            int(m.group(1)))
                        dailies.append( (name_node, when) )

        ret = []
        for name_node, when in dailies:
            board_node = name_node.parentNode

            board_entries = None
            for entries_node in board_node.getElementsByTagName('entries'):
                for child in entries_node.childNodes:
                    if child.nodeType == child.TEXT_NODE:
                        board_entries = int(child.data)
            assert board_entries != None

            # Skip empty dailies, since there are many bogus and future entries.
            if board_entries > 0:
                for url_node in board_node.getElementsByTagName('url'):
                    for child in url_node.childNodes:
                        if child.nodeType == child.CDATA_SECTION_NODE:
                            board_url = child.data.strip()
                            ret.append( (when, board_url, board_entries) )
        ret.sort()

        return ret

ENTRY_FIELDS = ['rank', 'score', 'steamid', 'ugcid', 'details']

def download_leaderboard(board_url):
    recs = []

    while True:
        print '  Downloading leaderboard at URL: %s' % board_url
        f = urlopen(board_url)
        dom = parse(f)

        entries = dom.getElementsByTagName('entry')
        for entry in entries:
            rec = {}
            for a in ENTRY_FIELDS:
                rec[a] = entry.getElementsByTagName(a)[0].childNodes[0].data.strip()
            recs.append(rec)

        # For dailies with >5000 entries, they are split into multiple requests.
        board_url = None
        for url_node in dom.getElementsByTagName('nextRequestURL'):
            for child in url_node.childNodes:
                if child.nodeType == child.CDATA_SECTION_NODE:
                    board_url = child.data.strip()
        if board_url == None:
            break

    return recs

# -> [(datetime.date, [{}])]
def read_dailies():
    # Some entries are bogus. All real boards have well over 100 entries, and all bogus boards well under.
    REAL_THRESHOLD = 100

    dailies = []

    csv_re = re.compile(r'daily_([0-9_]*)\.csv')
    csvs = [fn for fn in os.listdir('raw') if fn.endswith('csv')]
    for fn in csvs:
        path = os.path.join('raw', fn)
        rd = csv.DictReader(file(path, 'r'))
        recs = list(rd)

        date_str = csv_re.match(fn).group(1)
        when = datetime.datetime.strptime(date_str, '%Y_%m_%d').date()

        if len(recs) >= REAL_THRESHOLD:
            dailies.append( (when, recs) )

    return dailies

STEAM_ID_NULL = '-1'

def get_persona(steamid):
    # Download display name if we don't know it
    users_path = 'data/users'
    if not os.path.exists(users_path):
        os.mkdir(users_path)
    sum_path = os.path.join(users_path, '%s.txt' % steamid)
    if not os.path.exists(sum_path):
        sum_url = ('http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/?key=%s&steamids=%s' %
            (api_key, steamid))
        f = urlopen(sum_url)
        body = f.read()
        file(sum_path, 'w').write(body)

    # Find display name within the summary file
    f = file(sum_path, 'r')
    try:
        summary = json.load(f)
    except Exception:
        print 'Failed while loading persona JSON from %s' % sum_path
        raise
    persona = summary['response']['players'][0]['personaname']

    return persona

def format_ms(ms):
    cs = ms // 10
    s  = cs // 100
    m  = s  // 60

    disp_cs = cs % 100
    disp_s  = s  % 60

    return '%02d:%02d.%02d' % (m, disp_s, disp_cs)

def necrolab_points(rank):
    return 1.7 / (math.log(rank / 100.0 + 1.03) / math.log(10))

def inv_necrolab_points(points):
    return 100 * (10**(1.7/points) - 1.03)

import csv
import datetime
import json
import os
import os.path
import re
from urllib2 import urlopen
from xml.dom.minidom import parse

leaderboards_url = 'http://steamcommunity.com/stats/247080/leaderboards/?xml=1'
api_key = file('apikey.txt', 'r').read().strip()

# day/month/year
# example: 7/10/2015
daily_re = re.compile('([0-9]+)/([0-9]+)/([0-9]{4})_PROD')

# -> [(datetime.date, url string)]
class Leaderboards(object):
    def __init__(self):
        f = urlopen(leaderboards_url)
        self.dom = parse(f)

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

def download_daily(board_url):
    recs = []

    while True:
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

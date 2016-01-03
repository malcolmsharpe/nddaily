import datetime
import re
from urllib2 import urlopen
from xml.dom.minidom import parse

leaderboards_url = 'http://steamcommunity.com/stats/247080/leaderboards/?xml=1'

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
                            ret.append( (when, board_url) )
        ret.sort()

        return ret

ENTRY_FIELDS = ['rank', 'score', 'steamid', 'ugcid', 'details']

def download_daily(board_url):
    f = urlopen(board_url)
    dom = parse(f)

    entries = dom.getElementsByTagName('entry')
    recs = []
    for entry in entries:
        rec = {}
        for a in ENTRY_FIELDS:
            rec[a] = entry.getElementsByTagName(a)[0].childNodes[0].data.strip()
        recs.append(rec)

    return recs

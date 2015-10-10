import csv
import json
import os
import os.path
import re
import sys
from urllib2 import urlopen
from xml.dom.minidom import parse

# day/month/year
# example: 7/10/2015
date = sys.argv[1]
assert re.match(r'[0-9]+/[0-9]+/[0-9]{4}', date)
day, month, year = date.split('/')

api_key = file('apikey.txt', 'r').read().strip()

date_path = 'data/%s-%s-%s' % (year, month, day)
if not os.path.exists(date_path):
    os.mkdir(date_path)

# Find desired daily challenge leaderboard
leaderboards_url = 'http://steamcommunity.com/stats/247080/leaderboards/?xml=1'
f = urlopen(leaderboards_url)
dom = parse(f)

board_name = '%s_PROD' % date

names = dom.getElementsByTagName('name')

matches = []

for name in names:
    for child in name.childNodes:
        if child.nodeType == child.CDATA_SECTION_NODE:
            cdata = child.data
            if cdata.strip() == board_name:
                matches.append(name)

if len(matches) != 1:
    print 'ERROR: Unexpected number %d of leaderboards matching name %s' % (len(matches), board_name)
    sys.exit(1)

board_url = None

board_node = matches[0].parentNode
for url_node in board_node.getElementsByTagName('url'):
    for child in url_node.childNodes:
        if child.nodeType == child.CDATA_SECTION_NODE:
            board_url = child.data.strip()

assert board_url != None

# Read the daily challenge leaderboard
# TODO: Handle multi-response leaderboards
f = urlopen(board_url)
dom = parse(f)

n = 0
recs = []

entries = dom.getElementsByTagName('entry')
for entry in entries:
    rank = entry.getElementsByTagName('rank')[0].childNodes[0].data.strip()
    score = entry.getElementsByTagName('score')[0].childNodes[0].data.strip()
    steamid = entry.getElementsByTagName('steamid')[0].childNodes[0].data.strip()
    ugcid = entry.getElementsByTagName('ugcid')[0].childNodes[0].data.strip()
    details = entry.getElementsByTagName('details')[0].childNodes[0].data.strip()

    if len(details) != 16:
        continue
    zone, floor = int(details[1]), int(details[9])

    if ugcid == '-1':
        # missing replay?
        print '#%4s missing replay?' % rank
        continue

    # No real point wasting requests on non-wins,
    # as the time is not always recorded in the replay.
    if (zone, floor) != (4, 6):
        continue

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

    # Download metadata if we don't have it
    meta_path = os.path.join(date_path, '%s.json' % ugcid)

    if not os.path.exists(meta_path):
        meta_url = ('http://api.steampowered.com/ISteamRemoteStorage/GetUGCFileDetails/v1/'
            '?appid=247080&ugcid=%s&key=%s') % (ugcid, api_key)
        f = urlopen(meta_url)
        body = f.read()
        file(meta_path, 'w').write(body)

    # Download ugc if we don't have it
    f = file(meta_path, 'r')
    meta = json.load(f)
    ugc_url = meta['data']['url']

    uuid = ugc_url.split('/')[-2]

    ugc_path = os.path.join(date_path, '%s_%s.ugc' % (ugcid, uuid))

    if not os.path.exists(ugc_path):
        f = urlopen(ugc_url)
        body = f.read()
        file(ugc_path, 'w').write(body)

    # Find display name within the summary file
    f = file(sum_path, 'r')
    summary = json.load(f)
    persona = summary['response']['players'][0]['personaname']

    # Find run summary time within the UGC file
    f = file(ugc_path, 'r')
    ugc_data = f.read()
    parts = ugc_data.split('%*#%*')
    replay = parts[1]
    lines = replay.split('\\n')
    elapsed_ms = int(lines[8])

    elapsed_cs = elapsed_ms // 10
    elapsed_s = elapsed_cs // 100
    elapsed_m = elapsed_s // 60

    disp_cs = elapsed_cs % 100
    disp_s = elapsed_s % 60

    disp = '%02d:%02d.%02d' % (elapsed_m, disp_s, disp_cs)

    print '#%4s    %20s (%s)    %s    %s    %d-%d    (%s)' % (
        rank, persona, steamid, score, disp, zone, floor, ugcid)
    n += 1

    recs.append( (elapsed_ms, disp, persona, steamid, score) )

print
print 'Number of finishers = %d' % n
print

wr = csv.writer(file('out/%s-%s-%s.csv' % (year, month, day), 'w'))
wr.writerow( ['Run Duration', 'Persona', 'Steam ID', 'Score'] )

recs.sort()
for t, disp, pers, sid, score in recs:
    print '%s    %s' % (disp, pers)

    # Note: the purpose of the single-quote for the Steam ID is to force Google Sheets to interpret it as
    # plain text rather than a number. As a number, it can be converted to scientific notation.
    wr.writerow( [disp, pers.encode('utf_8'), "'" + sid, score] )

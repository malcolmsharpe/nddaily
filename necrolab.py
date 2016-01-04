# Rank using the Necrolab formula.

from collections import defaultdict
import datetime
import math

from common import *

TOP_NS = [1, 5, 10, 20, 50, 100]

dailies = read_dailies()

newest = max(when for when, recs in dailies)
print 'newest daily:  %s' % newest

# steam id str -> [(datetime.date when, int rank)]
id_ranks = defaultdict(lambda: [])

for when, recs in dailies:
    for rec in recs:
        steamid = rec['steamid']
        if steamid == STEAM_ID_NULL:
            continue
        rank = int(rec['rank'])

        id_ranks[steamid].append( (when, rank) )

# steam id, top n, total points, total dailies, total place
entries = []

def necrolab_points(rank):
    return 1.7 / (math.log(rank / 100.0 + 1.03) / math.log(10))

MAX_AGE = 100

for steamid in id_ranks:
    tops = len(TOP_NS) * [0]
    total_points = 0.
    total_dailies = 0
    total_place = 0

    for when, rank in id_ranks[steamid]:
        age = (newest - when).days

        if age >= MAX_AGE:
            continue

        for i, top_n in enumerate(TOP_NS):
            if rank <= top_n:
                tops[i] += 1
                break

        base = necrolab_points(rank)
        adj = base * ((MAX_AGE - age) / float(MAX_AGE))
        total_points += adj

        total_dailies += 1
        total_place += rank

    entry = []
    entry.append(steamid)
    entry.append(tops)
    entry.append(total_points)
    entry.append(total_dailies)
    entry.append(total_place)

    entries.append(entry)

entries.sort(key=lambda entry: entry[2], reverse=True)

RANKING_LEN = 100

print 'Unique players:  %d' % len(entries)
for steamid, tops, total_points, total_dailies, total_place in entries[:RANKING_LEN]:
    pd = total_points / total_dailies
    average_place = total_place // total_dailies

    print steamid, tops, total_points, pd, total_dailies, average_place

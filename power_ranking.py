# A daily challenge power ranking as described in
# https://masharpe.wordpress.com/2016/01/29/desired-incentives-for-daily-challenge-power-ranking/
# https://masharpe.wordpress.com/2016/01/30/decay-curves-for-daily-challenge-power-ranking/

import csv
from collections import defaultdict
import math
import numpy as np
import random

from common import *

eps = 1e-8

# How many recent days to ignore.
OLD = 1
#OLD = 17

print 'Skipping %d most recent days' % OLD

# Parameters

# 20% of your plays determine 80% of your score.
p = math.log(0.8) / math.log(0.2)
#p = 0.001

# This parameter allows a new player to catch up after 15 days of playing 20% better than opponent.
#a = math.log(1.2) / 15.0
a = math.log(1.2) / 30.0

print 'Parameters used:'
print '  p = %.4f' % p
print '  a = %.4f' % a

# Compute ranking
print 'Reading dailies'
dailies = read_dailies()

user_plays = defaultdict(lambda: [])

max_when = None

for when, recs in dailies:
    if max_when == None or when > max_when:
        max_when = when

    for rec in recs:
        steamid = rec['steamid']
        user_plays[steamid].append( (when, rec) )
print 'Most recent daily = %s' % max_when

scored = []
for steamid, plays in user_plays.items():
    results = []
    for when, rec in plays:
        t = (max_when - when).days

        t -= OLD
        if t < 0:
            continue

        #width = math.exp(-(a/p) * t) - math.exp(-(a/p) * (t+1))
        width = -math.expm1(-(a/p)) * math.exp(-(a/p)*t)

        rank = int(rec['rank'])
        points = necrolab_points(rank)

        results.append( (points, width) )

    results.sort(reverse=True)
    x1 = 0.0
    score = 0.0
    raw = 0.0
    ptp = 0.0 # ParTiciPation
    for height, width in results:
        x2 = x1 + width
        score += (x2**p - x1**p) * height
        raw += width * height
        ptp += width

        x1 = x2
    assert x1 <= 1 + eps

    scored.append( (score, raw, ptp, len(plays), steamid) )

scored.sort(reverse=True)

wtr = csv.writer(file('out/power_ranking.csv', 'w'))
wtr.writerow(['Rank', 'Persona', 'Score', 'Eqv Rank', 'Dailies', 'Participation', 'Raw Score', 'Steam ID'])

TOP_N = 50
CSV_MAX = 1000

print 'Top-ranked %d players:' % TOP_N
print '  %3s -- %30s -- Score -- ERank -- %5s -- %5s -- %17s' % ('N', 'Persona', 'Ptp', 'Raw', 'Steam ID')
for i, (score, raw, ptp, nplays, steamid) in enumerate(scored):
    if i >= CSV_MAX:
        break

    persona = get_persona(steamid)
    eqv_rank = inv_necrolab_points(score)

    if i < TOP_N:
        print '  %3d -- %30s -- %5.1f -- %5.2f -- %5.3f -- %5.1f -- %17s' % (i+1, persona, score, eqv_rank, ptp, raw, steamid)

    wtr.writerow([str(i+1), persona.encode('utf_8'), repr(score), repr(eqv_rank), str(nplays), repr(ptp), repr(raw), "'" + steamid])

from collections import defaultdict
import csv
import math

from common import *

boards = [
    ('Cadence', Leaderboards.CADENCE_SPEED),
    ('Dorian', Leaderboards.DORIAN_SPEED),
    ('Dove', Leaderboards.DOVE_SPEED),
    ]
chars = [x[0] for x in boards]

user_speeds_ms = defaultdict(lambda: {})
user_ranks = defaultdict(lambda: {})

print 'Downloading leaderboards'
for char, board_url in boards:
    print '    %s speed' % char
    recs = download_leaderboard(board_url)

    for rec in recs:
        steamid = rec['steamid']
        score = rec['score']
        rank = int(rec['rank'])

        speed_ms = 100000000 - int(score)
        user_speeds_ms[steamid][char] = speed_ms
        user_ranks[steamid][char] = rank
print 'Total users:  %d' % len(user_speeds_ms)

eligible = []
for user in user_speeds_ms:
    if len(user_speeds_ms[user]) == len(boards):
        eligible.append(user)
print 'Eligible users:  %d' % len(eligible)

def compute_user_necrolab(u):
    ret = 0.
    for rank in user_ranks[u].values():
        ret += necrolab_points(rank)
    return ret

def compute_user_score(u):
    ret = 0.
    for speed_ms in user_speeds_ms[u].values():
        ret += math.log(speed_ms)
    return ret
eligible.sort(key=lambda u: compute_user_score(u))

wr = csv.writer(file('out/cdd_rank.csv', 'w'))
header = ['Log Sum Score', 'Necrolab', 'Steam ID', 'Persona']
for char in chars:
    header.append(char + ' rank')
    header.append(char)
    header.append(char + ' (ms)')
wr.writerow(header)

print 'Writing CSV ranking'
for u in eligible[:100]:
    score = compute_user_score(u)
    # score = '=LN(G2)+LN(J2)+LN(M2)'
    necrolab = compute_user_necrolab(u)
    persona = get_persona(u)

    row = [score, necrolab, "'" + u, persona]
    for char in chars:
        rank = user_ranks[u][char]
        row.append(rank)

        time_ms = user_speeds_ms[u][char]
        pretty_time = format_ms(time_ms)
        row.append("'" + pretty_time)
        row.append(str(time_ms))
    wr.writerow(row)

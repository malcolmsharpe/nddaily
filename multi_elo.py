# Use a multiplayer Elo system for ranking.

import csv
from collections import defaultdict
import math
import numpy as np
import random
from scipy.optimize import minimize

from common import *
import elo_core

dry_run = False
print 'Dry run?  %s' % dry_run

print 'Reading dailies'
dailies = read_dailies()

print 'Indexing steam IDs and cleaning invalid entries'
index_of_steamid = {}
dailies_of_steamid = defaultdict(lambda: 0)
next_index = 0

alldata = []
for when, recs in dailies:
    out = []
    for rec in recs:
        steamid = rec['steamid']
        if steamid != STEAM_ID_NULL:
            out.append(rec)

            if steamid not in index_of_steamid:
                index_of_steamid[steamid] = next_index
                next_index += 1
            dailies_of_steamid[steamid] += 1
    alldata.append(out)

ndata = len(alldata)
nvalid = ndata // 5

random.seed(1234) # use a fixed seed for consistent results
validation_indexes = set(random.sample(range(ndata), nvalid))

training = []
validation = []

for i, row in enumerate(alldata):
    if i in validation_indexes:
        validation.append(row)
    else:
        training.append(row)
assert len(validation) == nvalid

print 'Split %d days into %d training points and %d validation points' % (
    ndata, len(training), len(validation))

def callback(xk):
    #print 'callback' #FIXME
    pass

# average negative log likelihood
#
# Uses repeated elimination, so the ranking is reversed and ratings negated.
def neg_log_lik(xs, data):
    m = 0
    tot_val = 0.
    tot_grad = np.zeros_like(xs)

    for recs in data:
        m += 1
        k = len(recs)
        rs = np.zeros(k)

        for i, rec in enumerate(reversed(recs)):
            steamid = rec['steamid']
            rs[i] = -xs[index_of_steamid[steamid]]

        val, grad = elo_core.f_np(rs)

        # negate value because f returns un-negated log likelihood
        tot_val -= val

        for i, rec in enumerate(reversed(recs)):
            steamid = rec['steamid']
            # this gradient is twice negated: once because we negate the value of f, and once because we
            # negated the input to f
            tot_grad[index_of_steamid[steamid]] += grad[i]

    tot_val /= m
    tot_grad /= m

    return tot_val, tot_grad

def objfun(xs):
    print '  objfun'

    val, grad = neg_log_lik(xs, training)

    # Apply regularization
    val += 0.5 * global_regu * np.sum(xs**2)
    grad += global_regu * xs

    print '   -> %.5f, |grad| = %.5f' % (val, np.linalg.norm(grad))

    return val, grad

def do_optimize(x0):
    options = {
        'disp': True,
    }
    if dry_run:
        options['maxiter'] = 1
    method = 'L-BFGS-B'
    #method = 'CG'
    res = minimize(objfun, x0, method=method, jac=True, callback=callback, options=options)

    print 'Optimization complete'
    print res

    return res.x

regu_nll = []

x0 = np.zeros(next_index)

regus = [1e-0, 3e-1, 1e-1, 3e-2, 1.8e-2, 1e-2, 5.6e-3, 3e-3, 1e-3]
if dry_run:
    regus = [1e-2]

for regu in regus:
    global_regu = regu

    print 'Optimizing with regularization %.5g' % global_regu

    x0 = do_optimize(x0)

    regu_nll.append((global_regu, x0))

best_regu = None
best_val_nll = None
best_x = None

print 'Regularization value results:'
for regu, res_x in regu_nll:
    train_nll = neg_log_lik(res_x, training)[0]
    val_nll = neg_log_lik(res_x, validation)[0]

    print '  %6.5g => valid %11.5f, train %11.5f' % (regu, val_nll, train_nll)

    if best_val_nll == None or val_nll < best_val_nll:
        best_regu = regu
        best_val_nll = val_nll
        best_x = res_x
print

global_regu = best_regu
print 'Re-optimizing on all data using regularization %.5g' % global_regu

final_x = do_optimize(best_x)

print 'Done optimizing'

f = file('multi_elo_final_x.dat', 'w')
for steamid, i in index_of_steamid.items():
    print >>f, steamid, repr(final_x[i])

elos = final_x

# Scale and translate using typical values.
elos = (400.0 / math.log(10.0)) * elos + 1500.0

ratings = []
for steamid, i in index_of_steamid.items():
    ratings.append((elos[i], steamid))
ratings.sort(reverse=True)

wtr = csv.writer(file('daily_elos.csv', 'w'))
wtr.writerow(['Elo', 'Dailies', 'Steam ID', 'Persona'])

DAILIES_THRESHOLD = 5
TOP_N = 50
CSV_MAX = 1000

nwritten = 0
nskipped = 0

print
print 'Top %d players by Elo:' % TOP_N
for i, (elo, steamid) in enumerate(ratings):
    if i >= CSV_MAX:
        break

    persona = get_persona(steamid)
    dailies = dailies_of_steamid[steamid]

    if i < TOP_N:
        print '  %3d -- %.1f in %4d -- %s -- %s' % (i+1, elo, dailies, steamid, persona)

    if dailies >= DAILIES_THRESHOLD:
        wtr.writerow([repr(elo), str(dailies), "'" + steamid, persona.encode('utf_8')])
        nwritten += 1
    else:
        nskipped += 1
print
print 'Wrote %d Elos' % nwritten
print 'Skipped %d players with fewer than %d dailies' % (nskipped, DAILIES_THRESHOLD)

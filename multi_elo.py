# Use a multiplayer Elo system for ranking.

import math
import numpy as np
from scipy.optimize import minimize

from common import *
import elo_core

print 'Reading dailies'
dailies = read_dailies()

print 'Indexing steam IDs and cleaning invalid entries'
index_of_steamid = {}
next_index = 0

cleaned = []
for when, recs in dailies:
    out = []
    for rec in recs:
        steamid = rec['steamid']
        if steamid != STEAM_ID_NULL:
            out.append(rec)

            if steamid not in index_of_steamid:
                index_of_steamid[steamid] = next_index
                next_index += 1
    cleaned.append(out)

def callback(xk):
    print 'callback'

regu = 1.0

# average negative log likelihood
#
# Uses repeated elimination, so the ranking is reversed and ratings negated.
def objfun(xs):
    print '  objfun'

    m = 0
    tot_val = 0.
    tot_grad = np.zeros_like(xs)

    for recs in cleaned:
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

    # Apply regularization
    tot_val += 0.5 * regu * np.sum(xs**2)
    tot_grad += regu * xs

    print '   -> %.5f, |grad| = %.5f' % (tot_val, np.linalg.norm(tot_grad))

    return tot_val, tot_grad

print 'Optimizing with regularization %.5g' % regu

x0 = np.zeros(next_index)
options = {
    'disp': True,
    'maxiter': 10, # FIXME
}
res = minimize(objfun, x0, method='L-BFGS-B', jac=True, callback=callback, options=options)

print 'Optimization complete'
print res
elos = res.x

# Scale and translate using typical values.
elos = (400.0 / math.log(10.0)) * elos + 1500.0

ratings = []
for steamid, i in index_of_steamid.items():
    ratings.append((elos[i], steamid))
ratings.sort(reverse=True)

TOP_N = 50
print
print 'Top %d players by Elo:' % TOP_N
for i in range(TOP_N):
    print '  %.5g -- %s' % ratings[i]

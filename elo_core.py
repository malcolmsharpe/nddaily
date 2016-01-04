# For background on the function being computed, see
# https://masharpe.wordpress.com/2016/01/04/notes-on-generalizing-elo-to-multiplayer-games-part-2/

import math
import numpy as np

def f_naive(rs):
    n = len(rs)

    val = 0.
    for i in range(n):
        num = math.exp(rs[i])
        den = 0.

        for j in range(i, n):
            den += math.exp(rs[j])

        val += math.log(num / den)

    grad = np.zeros_like(rs)
    for i in range(n):
        df = 1.
        for j in range(i+1):
            num = math.exp(rs[i])
            den = 0.
            for k in range(j, n):
                den += math.exp(rs[k])
            df -= num / den
        grad[i] = df

    return val, grad

def f_py(rs):
    n = len(rs)

    ss = np.zeros_like(rs)
    ss[n-1] = rs[n-1]
    for i in reversed(range(n-1)):
        ss[i] = max(rs[i], ss[i+1])

    Ps = np.zeros_like(rs)
    Ps[n-1] = 1
    for i in reversed(range(n-1)):
        Ps[i] = math.exp(rs[i] - ss[i]) + math.exp(ss[i+1] - ss[i]) * Ps[i+1]

    val = 0.
    for i in range(n):
        val += (rs[i] - ss[i]) - math.log(Ps[i])

    Gs = np.zeros_like(rs)
    Gs[0] = 1 / Ps[0]
    for i in range(1, n):
        Gs[i] = math.exp(ss[i] - ss[i-1]) * Gs[i-1] + 1 / Ps[i]

    grad = np.zeros_like(rs)
    for i in range(n):
        grad[i] = 1 - math.exp(rs[i] - ss[i]) * Gs[i]

    return val, grad

def f_np(rs):
    n = len(rs)

    ss = np.maximum.accumulate(rs[::-1])[::-1]

    Ps = np.zeros_like(rs)
    Ps[n-1] = 1
    for i in reversed(range(n-1)):
        Ps[i] = math.exp(rs[i] - ss[i]) + math.exp(ss[i+1] - ss[i]) * Ps[i+1]

    val = np.sum((rs - ss) - np.log(Ps))

    Gs = np.zeros_like(rs)
    Gs[0] = 1 / Ps[0]
    for i in range(1, n):
        Gs[i] = math.exp(ss[i] - ss[i-1]) * Gs[i-1] + 1 / Ps[i]

    grad = 1 - np.exp(rs - ss) * Gs

    return val, grad

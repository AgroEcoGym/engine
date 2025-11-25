
import numpy as np
def kappa(x, range):
    a, b = range
    xx = x - b if x > b else 0
    yy = x - a if x < a else 0
    return xx - yy

def glm(theta0, params):
    v = theta0
    for p in params:
        k = kappa(p[1], (p[2], p[3]))
        if k > 0:
            v += p[0] * k
    return v


def expglm(theta0, params):
    return np.exp(-glm(theta0, params))


def expglmnoisy(theta0, params, sigma2, np_random=np.random):
    return expglm(theta0, params) + np_random.normal() * sigma2
import random

_STATE = {"seed": None}


def seed_all(seed):
    random.seed(seed)
    _STATE["seed"] = seed


def normalize(x):
    s = sum(x)
    if s == 0:
        return x
    return [v / s for v in x]


def compute_default():
    return 1


def deco(f):
    return f


@deco
def decorated(x=compute_default()):
    return x


def fact(n):
    if n <= 1:
        return 1
    return n * fact(n - 1)


def dyn_x():
    return "dynamic"

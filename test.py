"""
Some simple tests
"""

import os
import sys
import doctest
from decorator import decorator


@decorator
def identity(f, *a, **k):
    "do nothing decorator"
    return f(*a, **k)


@identity
def f1():
    "f1"


def getfname(func):
    fname = os.path.basename(func.__globals__['__file__'])
    return os.path.splitext(fname)[0] + '.py'


def test0():
    this = getfname(identity)
    assert this == 'test.py', this


def test1():
    this = getfname(f1)
    assert this == 'test.py', this

if __name__ == '__main__':
    for name, test in list(globals().items()):
        if name.startswith('test'):
            test()

    if sys.version >= '3':
        import documentation3 as doc
    else:
        import documentation as doc

    err = doctest.testmod(doc)[0]
    sys.exit(err)

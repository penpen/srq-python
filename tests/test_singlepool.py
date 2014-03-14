#!/usr/bin/env python
# encoding: utf-8
import sys
sys.path.append("../srq")
import srq.singlepool as pool

WORK = False


def wrk(a, b):
    global WORK
    assert (a, b) == ('a', 4)
    WORK = True
    yield True


def test_pool():
    global WORK
    p = pool.Pool(10)
    assert isinstance(p, pool.Pool), 'pool creation'
    p.spawn(wrk, 'a', b=4)
    assert p.full() is False, 'pool not full'
    p.join()
    assert WORK is True, 'work test'
    WORK = False
    worker = p.spawn(wrk, 'a', 'b')
    p.killone(worker)
    p.join()
    assert WORK is False, 'task killed'
    p = pool.Pool(0)
    assert p.full() is True, 'pool full'

if __name__ == '__main__':
    test_pool()

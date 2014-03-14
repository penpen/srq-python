#!/usr/bin/env python
# encoding: utf-8
import sys
sys.path.append("../srq")
import srq
import re
import getpass
import platform
import redis


def wrk(a, b):
    assert (a, b) == ('test', 'blah'), 'worker test'
    return 'some result'


def test_queue():
    r = redis.StrictRedis(decode_responses=True)
    q = srq.Queue(r, 'test')
    assert q.tasks == 0, 'init values'
    assert q.results == 0, 'init values'
    # request work
    uuid = q.request('test', 'blah')
    assert q.tasks == 1, 'task queued'
    assert re.match(r'^[0-9a-z]{32}$', uuid), 'uuid is uuid'
    q.process(wrk)
    assert q.results == 1, 'got result'


def test_worker_name():
    name = srq.get_worker_name()
    name_regexp = '^{user}@{node}/[0-9a-z]{{16}}$'.format(user=getpass.getuser(),
                                                          node=platform.node())
    assert re.match(name_regexp, name), 'worker name'

if __name__ == '__main__':
    test_queue()
    test_worker_name()

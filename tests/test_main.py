#!/usr/bin/env python
# encoding: utf-8
import sys
sys.path.append("../srq")
import srq
import fakeredis
import re


def test_queue():
    r = fakeredis.FakeStrictRedis()
    q = srq.Queue(r, 'test')
    assert q.tasks == 0, 'init values'
    assert q.results == 0, 'init values'
    # request work
    uuid = q.request('test', 'blah')
    assert q.tasks == 1, 'task queued'
    assert re.match(r'^[0-9a-z]{32}$', uuid), 'uuid is uuid'


if __name__ == '__main__':
    test_queue()

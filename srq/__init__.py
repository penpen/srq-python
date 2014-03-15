# encoding: utf-8
import time

from gevent import monkey
monkey.patch_all()
from gevent.pool import Pool
from gevent import sleep

from uuid import uuid4

# worker name tools
import getpass
import platform

# JSON module
try:
    import ujson as json
except ImportError:
    import json

# Logger
import logging
logger = logging.getLogger(__name__)


def get_worker_name():
    return '{user}@{host}/{token}'.format(user=getpass.getuser(),
                                          host=platform.node(),
                                          token=uuid4().hex[:16])


class Queue(object):

    def __init__(self, redis, name, ttl=None):
        self._redis = redis
        self.name = name
        self.tasks_key = self._get_key_(name, 'tasks')
        self.result_key = self._get_key_(name, 'results')
        # For killing by timeout (memory leak)
        self.started = time.time()
        self.working = set()
        self._greenlets = []
        self.ttl = ttl
        self.worker = get_worker_name()
        # if show_stats:
        #    self.stats_start = time.time()
        #    self.tasks_processed = 0

    def _get_key_(self, name, token, modifier='queue'):
        return 'srq:{modifier}:{name}:{token}'.format(name=name, token=token, modifier=modifier)

    def process(self, func, pool=20, workers=[], stats=None):
        try:
            self._pool = Pool(pool)
            self.func = func
            self.spawn(self._get_work_)
            # if self.show_stats:
            #    self.spawn(self._show_stats_)
            for worker in workers:
                self.spawn(worker)
            if stats:
                self.spawn(self.push_stats, stats)
            self._pool.join()
        except Exception:
            logger.error('Gevent error', exc_info=True)

    def push_stats(self, fn):
        while True:
            stats = fn()
            self._redis.setex('srqstats:%s:%s' % (self.name, self.token), 6, stats)
            if sleep:
                sleep(5)
            else:
                yield 5

    def _show_stats_(self):
        while True:
            if time.time() - self.started > self.ttl:
                self.stop()
            elapsed = time.time() - self.stats_start
            speed = self.tasks_processed / elapsed
            print('Speed: %d t/s (%d tasks by %d sec)' % (speed, self.tasks_processed, elapsed))
            self.stats_start = time.time()
            self.tasks_processed = 0
            if sleep:
                sleep(5)
            else:
                yield 5

    def _get_work_(self):
        while True:
            if self.ttl:
                if time.time() - self.started > self.ttl:
                    self._pool.spawn(self.stop)
            if self._pool.full():
                sleep(5)
                continue
            task = self._redis.lpop(self.tasks_key)
            if task:
                self.spawn(self._work_, task)
            if sleep:
                sleep(5)
            else:
                yield 5

    def _work_(self, task_data):
        self.working.add(task_data)
        task = json.loads(task_data)
        uuid, args, kwargs = task
        logger.debug('Got task: %s', uuid)
        try:
            result = self.func(*args, **kwargs)
            self._push_result_(uuid, result)
            logger.debug('Processed: %s', uuid)
            if self.show_stats:
                self.tasks_processed += 1
        except Exception:
            logger.error('Proccessing error: #%s', uuid, exc_info=True)
        try:
            self.working.remove(task_data)
        except KeyError:
            pass

    def _push_result_(self, uuid, result):
        result = json.dumps((uuid, result))
        self._redis.rpush(self.result_key, result)

    @property
    def tasks(self):
        return self._redis.llen(self.tasks_key)

    @property
    def results(self):
        return self._redis.llen(self.result_key)

    def request(self, *args, **kwargs):
        logger.debug('Requesting {name}(*{args}, **{kwargs})'.format(name=self.name,
                                                                     args=str(args),
                                                                     kwargs=str(kwargs)))
        uuid = uuid4().hex
        task = (uuid, args, kwargs)
        self._redis.rpush(self.tasks_key, json.dumps(task))
        return uuid

    def pop_result(self):
        result = self._redis.lpop(self.result_key)
        if result:
            return json.loads(result)

    def pull_result(self):
        while True:
            result = self._redis.lpop(self.result_key)
            if result:
                yield json.loads(result)

    def spawn(self, fn, *args, **kwargs):
        greenlet = self._pool.spawn(fn, *args, **kwargs)
        self._greenlets.append(greenlet)
        return greenlet

    def stop(self):
        for greenlet in self._greenlets:
            self._pool.killone(greenlet)
        for task in self.working:
            self._redis.rpush(self.tasks_key, task)

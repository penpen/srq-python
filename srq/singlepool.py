# encoding: utf-8


class Pool(object):

    """ Simple generator pool """

    def __init__(self, workers_num):
        self.workers_num = workers_num
        self.generators = []

    def spawn(self, generator, *args, **kwargs):
        print(args, kwargs)
        g = generator(*args, **kwargs)
        self.generators.append(g)
        return g

    def join(self):
        while True:
            if not self.generators:
                break
            for generator in self.generators:
                try:
                    next(generator)
                except StopIteration:
                    self.generators.remove(generator)

    def killone(self, generator):
        self.generators.remove(generator)

    def full(self):
        if len(self.generators) >= self.workers_num:
            return True
        return False

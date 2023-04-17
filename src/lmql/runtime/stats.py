"""
Simple environment timer to measure the runtime of different parts of the
code. 

Usage:

stats = Stats("my_stats") # singleton instance

with stats.timer("my_tag"):
    # do something
"""

import time

class StatsTimer:
    def __init__(self, stats, tag):
        self.stats = stats
        self.tag = tag
        self.start = time.time()

    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        self.stats.count(self.tag, time.time() - self.start)

class Stats:
    stats = {}

    @staticmethod
    def print_all():
        for name, stats in Stats.stats.items():
            print(f"{name}:")
            print("\n".join(["\t" + line for line in str(stats).split("\n")]))
    
    def __new__(cls, name):
        if name not in cls.stats:
            cls.stats[name] = super().__new__(cls)
        return cls.stats[name]

    def __init__(self, name):
        self.times = {}

    def timer(self, tag):
        return StatsTimer(self, tag)

    def count(self, tag, time):
        if tag not in self.times:
            self.times[tag] = []
        self.times[tag].append(time)
    
    def __str__(self):
        return "\n".join([f"{tag}: {len(times)} calls, {sum(times)}s total, {sum(times)/len(times)}s avg" for tag, times in self.times.items()])


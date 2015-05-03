import time
import sys

class ConsoleLogger():
    def __init__(self): pass

    def log(self, message):
        """Write a message to the file."""
        timestamp = time.strftime("[%H:%M:%S]", time.localtime(time.time()))
        sys.stdout.write('%s %s\n' % (timestamp, message))
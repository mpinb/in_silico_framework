import time

timers = {}

def startTimer(name):
    timers[name] = time.time()

def writeTimer(name):
    delta = time.time() - timers[name] 
    print("time {}: {}".format(name, delta))
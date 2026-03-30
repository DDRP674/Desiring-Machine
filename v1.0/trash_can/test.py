import time
import gevent
from gevent.threadpool import ThreadPool

def f1():
    print("f1.s")
    gevent.sleep(1) # 不要用time，除非用monkey替换
    print("f1.e")

def f2():
    print("f2.s")
    gevent.sleep(1)
    print("f2.e")

def f3():
    print("f3.s")
    gevent.sleep(1)
    print("f3.e")

pool = ThreadPool(10)

a = pool.spawn(f1)
time.sleep(0.3)
b = pool.spawn(f2)
f3()
time.sleep(0.3)
# input()

import queue, threading, time

q = queue.Queue(maxsize=5)

def f():
    while True:
        s = input()
        if q.full(): q.get()
        q.put(s)

def g():
    while True:
        print(q.get())

threading.Thread(target=f, daemon=True).start()
threading.Thread(target=g, daemon=True).start()
time.sleep(1800)
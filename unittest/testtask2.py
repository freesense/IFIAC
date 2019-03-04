import time

from APP.invokerSHARE import TaskBase

class CTest1(TaskBase):
    pass


idx = 2
b, c = None, 0

def testtask2(*a, **kw):
    time.sleep(idx*60+59*2)
    global b, c
    c += 1
    n = time.localtime()
    if c == 1:
        b = time.localtime()
    else:
        print idx+1, n, b, '% 3d % 3d' % (c, (time.mktime(n)-time.mktime(b))/(c-1))

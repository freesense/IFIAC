
#coding:utf-8
from invokerSHARE import TaskBase


class test(TaskBase):
    def echo(*t, **d):
        #print '--', 12345678111222,len(t),t[-1]
         
        param = t[-1]

        try:
            if param:
                content = param.get('content')
            return content.encode('utf8')
        except:
            pass
        return 'haha'

    
import sys, time

class dummy:
    def __init__(self):
        self.Name = 'DUMMY'

    def __repr__(self):
        return 'Dummy Class'

    def __del__(self):
        print '... del dummy'

    def start(self):
        print 'dummy.start'

    def stop(self):
        print 'dummy.stop'

obj = None
count = 0

def init(*t, **d):
    global obj, count
    if obj is None:
        obj = dummy()
    count += 1
    d['publish'](obj, 'test', count)

def get(*t, **d):
    #time.sleep(60)
    #return str(d['get']('DUMMY.test'))*3
    #d['publish'](__name__, 'test', count)
    print '--', 1234567
    return 'HaHaBaBa'

def uninit(*t, **d):
    global obj, count
    time.sleep(60)
    del obj
    del count
    obj = None

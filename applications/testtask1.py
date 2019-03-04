import time
from invokerSHARE import TaskBase

class CTest(TaskBase):
    def start(self, *a, **kw):
        print 'CTest.start reload.....'
        
class CTest2(TaskBase):
    def start(self, *a, **kw):
        print 'CTest2.start reload.....'
      
class CTest3(TaskBase):
    pass
class CTest4(TaskBase):
    pass
#    def __del__(self):
#        print '... del dummy'
#
#    def start(self, *a, **kw):
#        print 'CTest.start'
#
#    def stop(self):
#        print 'CTest.stop'

class CTest5(TaskBase):
    pass
#    def cb(self, result):
#        for row in result[0]:
#            print row.acctcode, row.chsname, row.SubjectTypeOf, row.FinTypeOf
#
#    def start(self, *a, **kw):
#        pd = self.obj.PD
#        print '#######', pd
#        pd.run('select acctcode,chsname,SubjectTypeOf,FinTypeOf from Fin_Subject_Ref', self.cb)
#


idx = 1
b, c = None, 0

def testtask1(*a, **kw):
    time.sleep(idx*60+59*2)
    global b, c
    c += 1
    n = time.localtime()
    if c == 1:
        b = time.localtime()
    else:
        print idx+1, n, b, '% 3d % 3d' % (c, (time.mktime(n)-time.mktime(b))/(c-1))

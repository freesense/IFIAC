
#coding: utf-8

from invokerSHARE import TaskBase

class SubjectRef(TaskBase):
    def cb1(self, result,**kw):
        dCode = {}
        for row in result[0]:
            dCode[row.acctcode] = (row.chsname, row.SubjectTypeOf, row.FinTypeOf)
        self.SD.Fin_Subject_Ref = dCode
        print dCode.keys()
        print u'Fin_Subject_Ref Updated.'

    def start(self, *a, **kw):
        #self.obj.PD.db29.run('select acctcode,chsname,SubjectTypeOf,FinTypeOf from Fin_Subject_Ref', self.cb)
        self.SQL('select acctcode,chsname,SubjectTypeOf,FinTypeOf from Fin_Subject_Ref',[],self.cb1)
        self.testbinsert()
        
    def testbinsert(self):
        
        d = {'ddd':{'field':['f1','f2','f3'], 'data':[[0,1,2],[1,2,3]]},
         'eee':{'field':['a','b'], 'data':[['qq','ww'],['fvf','gbh'],['op[','...']]}}
        self.binsert(d)
        



# -*- coding: UTF-8 -*-
##############################################################################
#
# Copyright (c) Investoday Financial Information LTD.
#        File:  testSHARE.py
#      Author:  Frank Fan
# Start  Date:  2009.09.11
# Last modify:
#
##############################################################################
"""
"""


__version__='$Revision: 1.00 $'[11:-2]

from SHARE import printINI

def testSD():
    print SD.key
    data = {'a':1,'b':2}
    SD.save(data,'test')
    test = SD.load('test')
    print data,test
    SD.aaa = data
    #del SD.aaa
    print SD.aaa,data,SD.allkey


class a:
    def __init__(self):
        print 'test'
        
    def test(self):
        print 1112223333555777222
    def __del__(self):
        print '##del##'
        
def testReload():
    a = __import__('testshare')
    b = getattr(a,'a')
    
    test = getattr(b(),'test')
    test()
    

    
    
if __name__=='__main__':
    from SHARE import Stat
    st = Stat()
    print st.key
    testReload()
    #testSD()
    #printINI()
    

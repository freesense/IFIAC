# -*- coding: UTF-8 -*-
##############################################################################
#
# Copyright (c) Frank Fan
#        File:  APP_TOOLS.py
#      Author:  Frank Fan
# Start  Date:  2008.12.15
# Last modify:  
#
##############################################################################
"""共享工具
"""


__version__='$Revision: 1.00 $'[11:-2]


import os
import glob
from    shutil      import copy2

from gluon.storage import Storage,load_storage,save_storage 
from gluon.sql import SQLDB

from FP_TOOLS import *

__all__=['getFilePath','savePcl','loadPcl']


def getPathName(filename,path=''):
    """ 分解filename为路径和文件名，如果没有路径，用path替代

        @@return [path,name]                 
    """
    
    l = filename.rsplit('\\',1)
    if len(l) is 1:
        l = [path] + l
    return l

def getTreeFile(sourcepath,ext = '' ):
    """
    """
    
    lResult = []
    if ext:
        sourcepath = os.path.join(sourcepath,ext)
        #print sourcepath
    if sourcepath:
        lResult = glob.glob(sourcepath)

    return lResult

def savePcl(filename, storage, bak=True, path=''):
    """功能： 1.自动扩展名判断
             2.数据自动备份功能
             3.自动路径获取
             4.写失败数据自动恢复
        @@parameter path: 待存储数据路径
                    filename：带路径的文件名，如果没有，用path替代
                    storage: 待存储对象
                    bakDir:  备份目录，如果不为空，会自动生成 'data' 和 bakDir 子目录
    
    """
    ret = False
    
    if not filename:
        if not path: return ret
        filename = getFilename(path ,num = -3,ext = '.pcl')    #自动产生文件名类似'yyyymmddhhmmss.pcl'
        
    if filename.rsplit('.',1)[-1].lower() != 'pcl':#没有扩展名 加上缺省的pcl
        filename += '.pcl'
    
    path,fname = getPathName(filename, path)
    makeDir(path)
            
    if bak:    
        data_path = os.path.join(path,'data')
        bak_path =  os.path.join(path,'bak')
        #print bak_path
        makeDir(bak_path)
    else:
        data_path = path     
    makeDir(data_path)
    
    filename = os.path.join(data_path,fname)
    
    if bak and os.path.exists(filename):  #存在数据，do备份
        copy2(filename,os.path.join(bak_path,fname))

    try:    
        save_storage(storage, filename)     
        ret = True 
    except IOError, (errno, strerror):
##        if DEBUG:
##            print "Save %s %s"%(filename,ret)
##            print "I/O error(%s): %s" % (errno, strerror)
        
        if os.path.exists(os.path.join(bak_path,fname)):
            copy2(os.path.join(bak_path,fname),data_path)
      
    return ret

def loadPcl(filename,path=''):
    if filename.rsplit('.',1)[-1].lower() != 'pcl':#没有扩展名 加上缺省的pcl
        filename += '.pcl'

    path,fname = getPathName(filename,path)
    storage = None
    try:
        storage = load_storage(filename)
    except :
        data_path = os.path.join(path,'data')
        bak_path =  os.path.join(path,'bak')
        #print data_path,bak_path,os.path.join(data_path,fname)
        try:
            storage = load_storage(os.path.join(data_path,fname))
        except:
            if os.path.exists(os.path.join(bak_path,fname)):
                copy2(os.path.join(bak_path,fname),data_path)
                storage = load_storage(os.path.join(data_path,fname))
    return storage

def test():
    #o = Storage(a=1,b='333')
    o=[1,2,3]
    print 'Save object %s'%savePcl('aaa',o)
    O = loadPcl('aaa')
    return O
    
if __name__=='__main__':
    print test()
       
        

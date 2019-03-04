# -*- coding: UTF-8 -*-
##############################################################################
#
# Copyright (c) Investoday Financial Information LTD.
#        File:  pdfparser.py
#      Author:  Frank Fan
# Start  Date:  2009.09.07
# Last modify:
#
##############################################################################
"""
"""


__version__='$Revision: 1.00 $'[11:-2]

import os, sys, threading
from APP.FP_TOOLS import parseIni,makeDir,toStorage,Storage,getIniList,getLineList
from APP.APP_TOOLS import getTreeFile, getPathName,loadPcl, savePcl
from string import replace


from APP.accessql import PoolDB

def getHomePath():
    return os.getcwd()

def setINI(app_name):
    homepath = getHomePath()
    app_path = os.path.join( homepath,app_name )
    data_path = os.path.join( homepath ,'IVK_DATA')
    plat_path = os.path.join( homepath ,'etc')
    INI = parseIni(os.path.join(plat_path,'%s.ini'%app_name.lower()))

    INI.HOME_PATH = homepath
    INI.APP_NAME = app_name.upper()
    INI.APP_PATH = app_path
    INI.APPLICATIONS = os.path.join(homepath,INI.APPS_PATH )
    os.sys.path.append(INI.APP_PATH)
    os.sys.path.append(INI.APPLICATIONS)
    INI.DATA_PATH = os.path.join(data_path,app_name)
    INI.SD_PATH = os.path.join(data_path,INI.SD_PATH)
    INI.FD_PATH = os.path.join(data_path,INI.FD_PATH)
    INI.DB_POOLS = getIniList(INI.DB_POOLS)
    INI.AUTO = getIniList(INI.AUTO)
    INI.INVOKER  = getIniList(INI.INVOKER)

    INI.LOG_CONF = os.path.join(plat_path, INI.LOG_CONF)
    INI.LOG_KEYS = getLineList(INI.LOG_KEYS) 
    INI.LOG_PATH = os.path.realpath(os.path.join(homepath,'LOG',app_name.lower()))
    return INI

INI = setINI('invoker')

from APP.FP_TOOLS import myLog
LOG,LOG_LEVELS = myLog(INI.LOG_PATH, INI.LOG_CONF, INI.LOG_KEYS)

def logCon(msg,level):   
    debug_level = LOG_LEVELS.get(INI.DEBUG,99)
    if INI.DEBUG and debug_level <= LOG_LEVELS.get(level):
        eval('LOG["l_con"].%s(msg)'%INI.DEBUG)
        
def logSocket(msg,level):
    debug_level = LOG_LEVELS.get(INI.LOG_SOCKET,99)
    if INI.LOG_SOCKET and debug_level <= LOG_LEVELS.get(level):
        eval('LOG["l_socket"].%s(msg)'%INI.LOG_SOCKET)
        
def myLogging(msg,level,*a):
    """path:logpath
    """
    makeDir(INI.LOG_PATH)
    level = level.lower()
    if level not in LOG_LEVELS:
        msg += '\t LEVEL ERROR:%s  -->warning'%level 
        level = 'warning'
    
    for e in a:
        if e in INI.LOG_KEYS:
            eval('LOG[e].%s(msg)'%level) 
        else:
            s = '%s\t>>>Key Error: %s'%(msg,e) 
            eval('LOG["root"].%s(s)'%level) 
            writeroot = False            
    logCon(msg, level)
    logSocket(msg, level)
    
def printINI():
    for e in INI:
        print 'INI.%s=[%s]'%(e,INI[e])

def getModule(mod):
    if not mod:
        return None,None

    mod_path = INI.SCRIPT_PATH
    if mod.find('.') > 0:
        l = mod.split('.')
        if not l[0]:
            mod = l[1]  #'.module'
        else:
            mod_path,mod = l[0],'.'.join(l[1:])
    return '%s.%s'%(mod_path, mod),mod
    
def getFilePath(filename,path=''):
    if not path:
        path = INI.DATA_PATH
    return getPathName(filename,path)


class BASE:
    def __init__(self,*a,**kw):
        for e in kw:
            self.e = kw[e]

        self.getKey()
        print '##%s##'%self.key
        self.setDataName()
        self.bakdata = True

        self.init(*a,**kw)

    def init(self,*a,**kw):
        pass

    def getKey(self):
        self['classpath']=__name__
        #self.key='%s_%s'%(sys.argv[0].split('.')[0].split('\\')[-1],self.__class__.__name__)
        if self.classpath=='__main__':
            self['key']='%s.%s'%(sys.argv[0].split('.')[0],self.__class__.__name__)
        else:
            self['key']='%s.%s'%(self.classpath,self.__class__.__name__)

    def setDataName(self,data_name=None):
        if not data_name:
            data_name = self.key
        self.save_data_name = os.path.join(INI.DATA_PATH,data_name)
        print self.save_data_name

    def saveData(self,data,tag=None):
        if tag:
            save_data_name = '%s.%s'%(self.save_data_name,tag)
        else:
            save_data_name = self.save_data_name
            
        savePcl(save_data_name, data, self.bakdata )
        try:
            savePcl(save_data_name, data, self.bakdata )
        except:
            print "%s data save fail!"%save_data_name

    def loadData(self,tag=None):
        if tag:
            save_data_name = '%s.%s'%(self.save_data_name,tag)
        else:
            save_data_name = self.save_data_name
        try:
            return loadPcl(save_data_name)
        except:
            print '%s data not found!'%save_data_name
            
class DATA(Storage,BASE):
    def __init__(self,**kw):
   
        self['datalk'] = threading.RLock()      #写数据锁
        self['bakdata'] = True
        self.getKey()

        self.setDataName()
        try: __allkey = self.load()
        except:pass
        if not __allkey: __allkey = {}
        self['allkey'] = __allkey
        self.setkey(**kw)
        self.init()        

        
    def setkey(self, **kw):   
        for k,v in kw.items():
            self[k] = v       


    def init(self):
        """继承类初始化
        """
        pass           

    def save(self,data,tag=None):
        pclk = threading.RLock()        #写文件锁
        try:
            pclk.acquire()
            self.saveData(data,tag)
        finally:
            pclk.release()
            
    def load(self,tag=None):
        return self.loadData(tag)
        
    def loadall(self):
        for key in self['allkey']:
            try:
                self[key] = self.load(key)
            except:
                print 'File:%s.%s.pcl not Found!'%(self.save_data_name,key)
                
class SharedData(DATA):
    """SharedData in Memory
    """
    def init(self):
        print '##SD:%s##'%self.key
        self.loadall()  

    def __setattr__(self, key, value):
        self.save(value,key)         
        try:         
            self.datalk.acquire()
            self[key] = value            
            self['allkey'][key] = key
            self.save(self['allkey'])
        finally:
            self.datalk.release()
        
    def __delattr__(self, key):
        try: 
            self.datalk.acquire()
            self.allkey.pop(key)
            self.save(self['allkey'])            
            del self[key]
        except KeyError, k: 
            raise AttributeError, k
        finally:
            self.datalk.release()
            
    def __getattr__(self, key): 
        try: return self[key]
        except KeyError, k: 
            if key in self['allkey']:
                try: return self.load(key)
                except:pass
            return None
                    
    def setDataName(self,data_name=None):
        if not data_name:
            data_name = 'SD_%s'%self.key
        self['save_data_name'] = os.path.join(INI.SD_PATH,data_name)           
                 

   
#SD = SharedData()
#print '-'*40

class FileSharedData(SharedData):
    """ SharedData in files
    """
    
    def setDataName(self,data_name=None):
        if not data_name:
            data_name = 'FD_%s'%self.key
        self['save_data_name'] = os.path.join(INI.FD_PATH,data_name) 
 
  
    def getTfilelist(self, sources = None):
        if not sources:
            sources = INI.TEMPLATE
        #print sources  
        try:
            tflist = getTreeFile(sources,INI.TPL_FILES)

        except:
            tflist = {}
        return tflist
           
    def __getattr__(self, key): 
        if key in self['allkey']:
            try: return self.load(key)
            except:pass
        else:#处理其他的数据路径
            L = key.split('.')
            if len(L) > 1 and L[0] in INI.FD_READ_PATHS:
                path = INI.FD_READ_PATHS[L[0]]
                
                try:return self.loadPcl(save_data_name)
                except:
                    print 'File: %s not found!'%key
        return None  
    
    def __setattr__(self, key, value):
        self.save(value,key)         
        try:         
            self.datalk.acquire()        
            self['allkey'][key] = key
            self.save(self['allkey'])
        finally:
            self.datalk.release()
        
    def __delattr__(self, key):
        try: 
            self.datalk.acquire()
            self.allkey.pop(key)
            self.save(self['allkey'])            
        except KeyError, k: 
            raise AttributeError, k
        finally:
            self.datalk.release()    
                 
#FD = FileSharedData()


        
     
        




        

# -*- coding: UTF-8 -*-
##############################################################################
#
# Copyright (c) Frank Fan
#        File:  APP_TOOL.py
#      Author:  Frank Fan
# Start  Date:  2008.12.15
# Last modify:  
#
##############################################################################
"""共享工具
"""


__version__='$Revision: 1.00 $'[11:-2]

import os
import time, copy
import cPickle
from gluon import portalocker


__all__=['parseIni','makeDir','toStorage','getFilename',
         'Storage','load_storage','save_storage']


def parseIni(filename):
    """
    Read a special text(Ini) file, and then parse it to a  Storage(Dict)
    The text file format as following:
      Key = Value
    """
    
    d = {}
    stemp = ''
    for line in open(filename,'r').readlines():
        s = line.strip()
        if s == '' or s[0] == '#':  continue
        #s = s.split('#')[0]
        l = s.split('#')
        
        #处理#转义
        ss = ''
        for k in range(len(l)):
            s1 = l[k]
            if s1 and s1[-1]=='\\':  
                ss += s1[:-1] + '#'
                continue
            else:
                s = ss + s1
                break
            
        #处理跨行        
        if s and s[-1]=='\\':
            stemp += s[:-1]  
            continue
        elif stemp:
            s = stemp + s
            stemp = ''  

        l = [e.strip() for e in s.split('=',1)]
    
        if len(l) == 2:
            if l[1].isdigit():
                value = int(l[1])
            elif l[1] and l[1][0] in ['[','{','(']:
                try:
                    value = eval(l[1])
                except:
                    value = l[1]               
            else:
                value = l[1]               
        elif len(l) > 2:
            value = '='.join(l[1:])
        else: continue
    
        key = l[0].upper()
        if key in d:
            if isinstance(d[key],list):
                d[key].append(value)
            else:
                d[key] = [d[key],value]
        else:
            d[key] = value
    return Storage(d)

def getIniList(items):
    """
    """
    if not items:
        return []

    if not isinstance(items, list):
        items = [items]
    return items   
    
def getLineList(line,sep=',',keyUpper=False):
    if keyUpper:
        return [e.strip().upper() for e in line.split(sep)]
    else:
        return [e.strip().lower() for e in line.split(sep)]

def getDictItem(lResult):
    d = Storage()
    for item in lResult:
        try:
            w,r = item.split('=')
            d[w.strip().upper()] = r.strip()
        except:
            continue
    return d        

def replaceString(_s,kw):
    '''kw = {'key1':[value1,value2],'value3':'key2'}
    '''
    s  = copy.copy(_s)
    if s:
        for k,v in kw.items():
            if isinstance(v,list):
                for e in v:
                    s = s.replace(e,k)
            else:
                s = s.replace(k,v)
    return s
                   
def makeDir(*fPath):
    """创建path指定的目录，并进入。
    """
    if not fPath: return
    fpath = '\\'.join(fPath)
 
    if not  os.path.exists(fpath):
        os.makedirs(fpath)
    os.chdir(fpath)

def getFilename( *a, **kw):
    """ num: -3 : 'yyyymmddhhmmss'
                  3 : 'yyyymmdd'
        ext      :extend filename
        a       : list for path
    @@return filename such as path\...a\'yyyymmddhhmmss'+name
    """
    
    stylenum = kw.get('num',3)
    ext = kw.get('ext','')
    filename = ''.join(['%02d'%e for e in time.localtime()[:stylenum]])
    return os.path.join('\\'.join(a),filename + ext)

def listDirectory(file_path):
    """列出指定file_path目录下的所有子目录名称列表。
    """
    lResult = []
    if file_path and os.path.exists(file_path):
        flist = os.listdir(file_path)
        for line in flist:
            filepath = os.path.join(file_path,line)
            if os.path.isdir(filepath):
                lResult.append((filepath,line))
    return lResult

def getLastItem(s,sep='\\'):
    return s.rsplit(sep ,1)[-1]

def _listDirFiles(file_path,lfiles):
    """递归调用,列出file_path目录下的所有文件子目录文件,
       存放于lfiles  
    """
    if file_path and os.path.exists(file_path):
        flist = os.listdir(file_path)
        for line in flist:
            filepath = os.path.join(file_path,line)
            if os.path.isdir(filepath):
                _listDirFiles(filepath, lfiles)
            elif os.path.isfile(filepath):
                lfiles.append(filepath)
    return lfiles     
    
def listDirFiles(file_path, *lExt):
    """ 列出file_path目录下的所有文件子目录文件以及指定扩展名的文件(全路径)
        lExt like 'pdf','doc','txt'
        @@return dResult
            dResult like
                 dResult.all = [...]
                 dResult.pdf = [...]
                 dResult.doc = [...]
                 dResult.txt = [...]
                 
    """
    lResult = _listDirFiles(file_path,[])
    
    dResult = Storage()
    dResult.all = lResult
    lExt = [e.lower() for e in lExt]
    for ext in lExt:
        dResult[ext] = []
    for line in lResult:
        filepath = os.path.join(file_path,line)
        lext = filepath.rsplit('.',1)
        if len(lext) == 2:
            fpath, ext = lext
            ext = ext.lower()
            if ext in lExt:
                dResult[ext].append(filepath)
                
    dResult['total'] = []
    for ext in lExt:
        dResult['total'] += dResult[ext] 
    return dResult

def toStorage(Data,data=None):
    if isinstance(Data,list):
        data = []
        for item in Data:
            #print item
            #d = item
            #print d
            if isinstance(item,list) or isinstance(item,dict):
                data.append( toStorage(item))
            else:
                data.append(item)               

    if isinstance(Data,dict):
        data = Storage(Data)
        for item in Data:
            if isinstance(Data[item],list) or isinstance(Data[item],dict):
                data[item] = toStorage(Data[item])
            else:
                data[item] = Data[item]
    return data  

def toDict(Data,data=None):
    if isinstance(Data,list):
        data = []
        for item in Data:
            #print item
            #d = item
            #print d
            if isinstance(item,list) or isinstance(item,dict):
                data.append( toDict(item))
            else:
                data.append(item)               
    if isinstance(Data,dict):
        data = dict(Data)
        for item in Data:
            if isinstance(Data[item],list) or isinstance(Data[item],dict):
                data[item] = toDict(Data[item])
            else:
                data[item] = Data[item]       
    return data

def toString(Data,data=None):
    if isinstance(Data,list):
        data = []
        for item in Data:
            #print item
            #d = item
            #print d
            if isinstance(item,list) or isinstance(item,dict):
                data.append( toStorage(item))
            else:
                data.append(item)
                
    if isinstance(Data,dict):
        data = Storage(Data)
        for item in Data:
            if isinstance(Data[item],list) or isinstance(Data[item],dict):
                data[item] = toStorage(Data[item])
            else:
                data[item] = Data[item]    
    return data  

class Storage(dict):
    """
    A Storage object is like a dictionary except `obj.foo` can be used
    in addition to `obj['foo']`.
    
        >>> o = Storage(a=1)
        >>> o.a
        1
        >>> o['a']
        1
        >>> o.a = 2
        >>> o['a']
        2
        >>> del o.a
        >>> o.a
        None
    
    """
    def __getattr__(self, key): 
        try: return self[key]
        except KeyError, k: return None
    def __setattr__(self, key, value): 
        self[key] = value
    def __delattr__(self, key):
        try: del self[key]
        except KeyError, k: raise AttributeError, k
    def __repr__(self):     
        return '<Storage ' + dict.__repr__(self) + '>'
    def __getstate__(self): 
        return dict(self)
    def __setstate__(self,value):
        for k,v in value.items(): self[k]=v

def load_storage(filename):
    file=open(filename,'rb')
    portalocker.lock(file, portalocker.LOCK_EX)    
    storage=cPickle.load(file)
    portalocker.unlock(file)    
    file.close()
    return toStorage(storage)

def save_storage(storage,filename):    
    file=open(filename,'wb')
    portalocker.lock(file, portalocker.LOCK_EX)
    cPickle.dump(toDict(storage),file)
    portalocker.unlock(file)    
    file.close()
    
LOG_LEVEL = ['debug','info','error','warn','warning','critical']
 
def myLog(logpath, logconf, logkeys):
    import logging
    import logging.config

    makeDir(logpath)
    logging.config.fileConfig(logconf)
    log = Storage()
    for e in logkeys:
        if e == 'root':
            log[e]= logging.getLogger()
        else:
            log[e] = logging.getLogger(e)
        log[e].debug('%s start...'%e)
    dLevel = {}
    for e in LOG_LEVEL:
        dLevel[e] = eval('logging.%s'%e.upper())
    return log, dLevel

from accessql import PoolDB
def buildPoolDB(db_pools):
    dPD = Storage()

    for pd in db_pools:
        try:
            pdstr,pdconn = pd.split('//')
            pdstr = '%s,5,10'%pdstr
            pdname, mixnum, maxnum = pdstr.split(',')[:3]
            dPD[pdname] = PoolDB(pdconn, int(mixnum), int(maxnum))
        except:
            print 'PD Define Error: ', pd
            continue
    return dPD

def chgCoding(msg,scoding ='utf-8', coding = 'gbk', unicoding= False):
    """utf-8 <--> coding,编码字串要避免混用编码
    """
    if unicoding:
        if not isinstance(msg,unicode):
            msg = unicode(msg,scoding)
        return msg

    try:
        msg = unicode(msg,scoding).encode(coding)
    except:
        try:
            msg = msg.encode(coding)
        except:
            pass
    return msg



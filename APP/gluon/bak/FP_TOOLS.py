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
import time
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
    for line in open(filename,'r').readlines():
        s = line.strip()
        if s == '' or s[0] == '#':  continue
        l = [e.strip() for e in s.split('#')[0].split('=',1)]
        if len(l) == 2:
            if l[1].isdigit():
                d[l[0].upper()] = int(l[1])
            else:
                d[l[0].upper()] = l[1]               
        elif len(l) > 2:
            d[l[0].upper()] = '='.join(l[1:])
                        
    return Storage(d)


def listPath(path):
    if ':' not in path:
        path = os.path.join(os.getcwd(),path)
        
    s = path.replace('\\','/')
    l = [e.strip() for e in s.split('/') if e]
    return l

    
def makeDir(path):
    if not path: return
    dirs = listPath(path)
    path = dirs[0]+'\\'
    for dir in dirs[1:]: 
        path = os.path.join(path, dir)
        if not os.path.exists(path):
            os.mkdir(path)
        else:
            os.chdir(path)
            

def getFilename(path = '', name = '', *a):
    """@@return filename such as path\...a\'yyyymmddhhmmss'+name
    """
    filename = ''.join(['%02d'%e for e in time.localtime()[:-3]])
    return os.path.join(path,''.join(a),filename+name)

            
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



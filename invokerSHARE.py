# -*- coding: UTF-8 -*-
##############################################################################
#
# Copyright (c) Investoday Financial Information LTD.
#        File:  pdfparser.py
#      Author:  Frank Fan
# Start  Date:  2009.09.17
# Last modify:
#
##############################################################################
"""
"""


__version__='$Revision: 1.00 $'[11:-2]


import threading

from APP.accessql import batch_insert, batch_update
from SHARE import SharedData, getModule
class IVKERROR(BaseException):pass


class Stat(SharedData):
    def init(self):
        self.setkey(_taskmap = {}, #任务表 key = task,存放原始任务指令（INI.INVOKER）
                    _modmap = {},  #共享模块表 key = module,存放module对象，用于reload
                    _objmap = {},  #对象表 key = id,
                    cmdmap = {},    #调度表：([module,class,startfunc,stopfunc],[(call,defer)],{prop})
                    _jobmap = {},  #作业表（运行态，不必保存）
                    _objlk = threading.RLock() ,     #对象表锁
                    _maplk = threading.RLock() ,     #调度表锁
                    _modlk = threading.RLock()  ,    #模块表锁
                    _joblk = threading.RLock()      #作业表锁

                    )
        print '##ST:%s##'%self.key
        self.loadall()

    def setTask(self,tasks,addFunc = None):
        """解析tasks参数，补齐缺省项目.
        @param :
            @@ tasks: (cmd,mods,prop)
                      mods:[module,class,start,stop]
        """

        for task in tasks:
            #task.append(dict())
            cmd,mods = task[:2]
            ivk = []
            for a,b in zip([None,None,'start','stop'],\
                           (mods + [None,None,None])[:4]):
                if b:
                    ivk.append(b)
                else:
                    ivk.append(a)

            prop = dict()
            if len(task)==3:
                prop = task[2]
            if addFunc:
                addFunc(cmd,ivk,prop)
            else:
                self.add_invoke(cmd,ivk,prop)

    def setMod(self,obj,s_module):
        try:
            self._modlk.acquire()
            self._modmap[s_module] = obj
        finally:
            self._modlk.release()

    def delJob(self,cmd):
        try:
            self._joblk.acquire()
            self._jobmap.pop(cmd)
        except:pass
        finally:
            self._joblk.release()

    def setJob(self,job,cmd):
        try:
            self._joblk.acquire()
            self._jobmap[cmd] = job
        finally:
            self._joblk.release()

    def getJob(self,cmd):
        return self._jobmap.get(cmd)

    def loadModule(self, s_module):
        """装载模块
        s_module: 模块名称
        """
        _mod = self._modmap.get(s_module)
        if not _mod:
           _mod =  self._loadModule(s_module)
        return _mod

    def _loadModule(self,s_module):
        module, mod = getModule(s_module)
        _mod =  __import__(module)
        _mod = getattr(_mod, mod)
        self.setMod(_mod,s_module)
        return _mod

    def add_invoke(self, cmd, ivk, prop):
        """向作业调度表中添加一项作业
        cmd     作业名称
        ivk     调用方法,['module', 'class','startfunc','stopfunc']
        prop    作业参数,{'autoload':1}
        """
        if cmd in self.cmdmap:
            return

        s_module, s_class, s_start, s_stop = ivk
        _mod = self.loadModule(s_module)
        assert self.loadClass(s_module, s_class, prop) is not None

        try:
            self._maplk.acquire()
            self.cmdmap[cmd] = (ivk, [], prop)
            self.saveData(self.cmdmap, 'cmdmap')
        finally:
            self._maplk.release()

    def loadClass(self, s_module, s_class, prop = None, isreload = False):
        """实例化类
        s_module:  模块名称
        s_class:  类名字符串
        prop:share:  类共享标志
        isreload: 是否reload标志，表示使用已经实例化的类。否则重新生成。
        """

        c_name = '%s.%s'%(s_module, s_class)
        if not prop:
            share = False
        else:
            share = 'share' in prop

        print 'loadClass:',s_module, s_class, share,c_name,self._objmap.keys()

        if share and (not isreload) and (c_name in self._objmap):#
            return self._objmap[c_name]
        else:
            _mod = self.loadModule(s_module)
            if _mod:
                try:
                    self._objlk.acquire()
                    _class = getattr(_mod, s_class)
                    _classObj = _class(self.obj)

                    print '##',s_module,id(_classObj)
                    if share :
                        print '*'*60
                        self._objmap[c_name] = _classObj

                    return _classObj
                finally:
                    self._objlk.release()
            else:
                print 'Unable to load class %s.%s.'%(s_module, s_class)

    def loadFunction(self,  s_module, s_class, s_start, s_stop, prop = dict()):
        """装载类方法
        s_module:  模块名称
        s_class:  类名字符串
        """
        classObj = self.loadClass(s_module, s_class,prop)
        return self._loadFunction(classObj, s_start, s_stop)

    def _loadFunction(self, classObj, s_start, s_stop):
        """装载类方法
        classObj 类对象实例
        """
        if classObj:
            try:
                _start = getattr(classObj, s_start)
                _stop = getattr(classObj, s_stop)
                return _start,_stop
            except AttributeError,e:
                print e
                return None,None


    def funcReload(self,cmd,func):
        try:
            self._joblk.acquire()
            job = self.getJob(cmd)
            if job.running:
                job.stop()
                job.funcReload(func)
                job.start(job._schedule)
            else:
                job.funcReload(func)
        except:pass
        finally:
            self._joblk.release()

    def getModCmd(self,s_module):
        lCmd = []
        for cmd in self.cmdmap:
            [s_mod, s_class, s_start, s_stop], invoke_obj, prop = self.cmdmap[cmd]
            if s_module == s_mod:
                lCmd.append([cmd,s_mod, s_class, s_start, s_stop, prop])
        return lCmd

    def modReload(self, s_module):
        msg = ''
        _mod = self.loadModule(s_module)
        if _mod:
            reload(_mod)
            msg += u'模块：%s 重载成功！\n'%s_module

            for cmd,s_mod, s_class, s_start, s_stop, prop in self.getModCmd(s_module):
                classObj = self.loadClass(s_module,s_class, prop, isreload = True)
                _start, _stop = self._loadFunction(classObj, s_start, s_stop)
                self.funcReload(cmd,_start)
                #print 'reload module function:%s.%s success!'%(s_class,s_start)
                msg += u'任务：%s 对象：%s.%s 重载成功！\n'%(cmd, s_class,s_start)

            for c_name in self._objmap:
                print c_name
                l = c_name.split('.')
                _s_module = '.'.join(l[:-1])
                if _s_module == s_module:
                    s_class = l[-1]
                    _classObj = self.loadClass(s_module,s_class,prop,isreload = True)

                    print 'reload share module:%s success!'%s_module
                    msg += u'共享对象：%s 重载成功！'%s_module
            return (0, msg)
        else:
            print s_module, 'not found.'
            return (65800, u'模块：%s 没找到！'%s_module)

class TaskBase:
    def __init__(self,obj):
        self.getKey()
        self.obj = obj
        self.SD = obj.SD
        if hasattr(obj,'PD'):
            self.PD = obj.PD
        self.INI = obj.INI
        self.init()

    def getKey(self):
        self.classpath=__name__
        #self.key='%s_%s'%(sys.argv[0].split('.')[0].split('\\')[-1],self.__class__.__name__)
        if self.classpath=='__main__':
            self.key = '%s.%s'%(sys.argv[0].split('.')[0],self.__class__.__name__)
        else:
            self.key = '%s.%s'%(self.classpath,self.__class__.__name__)

    def init(self):
        print 'Init ... :%s'%self.key,id(self)

    def __del__(self):
        print '... del:%s'%self.key,id(self)

    def start(self, *a, **kw):
        print '%s.start'%self.key

    def stop(self):
        print '%s.stop'%self.key

    def SQL(self,sql,param=None,cb=None,eb=None):
        if not cb:
            cb = self.cb
        self.PD.db29.run(sql,param,cb)

    def cb(self, result, **kw):
        print '%s.cb'%self.key

    def binsert(self,dData):
        batch_insert(self.PD.db29,dData)

    def bupdate(self,dData):
        batch_update(self.PD.db29,dData)
if __name__=='__main__':
    Stat()


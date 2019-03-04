
#coding:utf-8

import hashlib, threading, sys, new
from auth import *
from twisted.internet import reactor, defer
from twisted.internet.protocol import Protocol, ServerFactory, ClientFactory
from xml.dom.minidom import parseString
from xml.etree.ElementTree import ElementTree, Element, SubElement
from time import strftime, localtime
from twistedschedule.task import ScheduledCall
from twistedschedule.cron import CronSchedule
from twisted.python.threadpool import ThreadPool

from APP.FP_TOOLS import buildPoolDB


#线程池的最大最小并行线程数量
MaxPool = 50
MinPool = 5

from SHARE import INI, getModule,SharedData
from invokerSHARE import Stat,IVKERROR

class SimpleProtocol(Protocol):
    def __del__(self):
        print '...del SimpleProtocol'

    def connectionMade(self):
        self.data = ''
        self.transport.write(self.factory.data)

    def dataReceived(self, data):
        self.data += data
        tail = self.data.rfind('</answer>')
        if -1 != tail:
            _md5 = self.data[0:32]
            self.data = self.data[32:tail+len('</answer>')]
            m = hashlib.md5()
            m.update(self.data)
            if m.hexdigest() != _md5:
                self.data = "<?xml version='1.0' encoding='utf-8' standalone='yes' ?><answer ret='65501'>MD5校验失败</answer>"
            self.factory.cb(self.data, self.factory.param)
            self.transport.loseConnection()

class SimpleFactory(ClientFactory):
    protocol = SimpleProtocol

    def __init__(self, data, cb, eb, param = None):
        self.connector = None
        self.data, self.cb, self.eb, self.param = data, cb, eb, param

    def __del__(self):
        print '...del SimpleFactory'

    def clientConnectionFailed(self, connector, reason):
        if self.eb:
            self.eb(reason)

    def clientConnectionLost(self, connector, reason):
        del self.connector.transport
        self.connector = None


class InvokerProtocol(Protocol):
    def __init__(self):
        self.request = ''

    def connectionMade(self):
        self.factory.numProtocols += 1

    def connectionLost(self, reason):
        self.factory.numProtocols -= 1

    def onMessage(self, ans, serial = None):
        code, msg = ans
        if serial:
            print '>>> Protocol.onMessage', serial.encode('gbk'), msg.encode('gbk')
        else:
            print '>>> Protocol.onMessage', msg.encode('gbk')

        if serial is None:
            msg = u"<answer ret='%d'>%s</answer>" % (code, msg)
        else:
            msg = u"<answer ret='%d' serial='%s'>%s</answer>" % (code, serial, msg)
        msg = u"<?xml version='1.0' encoding='utf-8' standalone='yes' ?>" + msg
        m = hashlib.md5()
        msg = msg.encode('utf8')
        m.update(msg)
        msg = m.hexdigest()+msg
        self.transport.write(msg)

        if serial is None:
            self.transport.loseConnection()
        else:
            self.ans_count += 1
            if self.ans_count == len(self.reqs):
                self.transport.loseConnection()

    def parse(self):
        dom = parseString(self.request)
        root = dom.documentElement
        self.auth = root.getElementsByTagName('auth')[0]
        self.reqs = root.getElementsByTagName('command')
        self.ans_count = 0

        #析出认证元素
        authitems = {}
        options = self.auth.getElementsByTagName('option')
        for option in options:
            authitems[option.getAttribute('name')] = option.childNodes[0].data

        #解析所有命令
        cmds = [2, self]
        self.iReturnCount = 0
        for sr in self.reqs:
            cron_table = ''
            cmd = sr.getAttribute('cmd')
            type = sr.getAttribute('flag')
            serial = sr.getAttribute('serial')
            param = {}
            params = sr.getElementsByTagName('param')

            for pa in params:
                pa_name = pa.getAttribute('name')
                pa_value = pa.childNodes[0].data
                if pa_name == 'cron':
                    cron_table = pa_value
                elif pa_name in ['async_callback_end', 'peer_address']:
                    self.onMessage((65500, u'参数不可使用%s关键字' % pa_name), serial)
                    return
                param[pa_name] = pa_value
            cmds.append((cmd, type, serial, param, cron_table))

        self.factory.auth.batch_process(cmds, authitems, self.transport.client)

    def process(self, cmd, type, serial, param, cron, akey = None):
        def cb(call):
            if call is None:
                return

            if akey is None:
                call = u'<answer ret="0" serial="%s" auth="">%s</answer>' % (serial, call)
            else:
                call = u'<answer ret="0" serial="%s" auth="%s">%s</answer>' % (serial, akey, call)
            call = u"<?xml version='1.0' encoding='utf-8' standalone='yes' ?>" + call
            call = call.encode('utf8')
            m = hashlib.md5()
            m.update(call)
            call = m.hexdigest()+call
            self.transport.write(call)
            self.ans_count += 1
            if self.ans_count == len(self.reqs):
                self.transport.loseConnection()

        param['async_callback_end'] = cb
        param['peer_address'] = '%s:%d' % (self.transport.client)
        ans = self.factory.process(cmd, type, param, cron)
        if isinstance(ans, tuple):
            self.onMessage(ans, serial)
        else:
            ans.addCallback(cb)


    def dataReceived(self, data):
        """接收、解析、调度用户命令
        """
        self.request += data.lower()
        tail = self.request.rfind(self.factory.endreq)
        if -1 != tail:
            _md5 = self.request[0:32]
            self.request = self.request[32:tail+len(self.factory.endreq)]
            m = hashlib.md5()
            m.update(self.request)
            if m.hexdigest() != _md5:
                self.onMessage((65501, 'MD5校验失败'))
                self.transport.loseConnection()
                return

            self.parse()
            self.request = ''


class InvokerFactory(ServerFactory):
    """
    对象表：objname: (id(obj), obj)
    调度表：cmdname: ([module,class,startfunc,stopfunc],[(call,defer)],{prop})
    模块表：modname: (mod_object,[cmdname])
    """

    def __init__(self, protocol):
        self.protocol = protocol
        self.endreq = '</request>'

        self.numProtocols = 0               #统计并发数
        self.idInvoke = 0                   #调用对象id标志
        self.bReady = False                 #是否初始化完成，可以提供服务

        #状态对象
        SD = self.SD = SharedData()
        self.INI = INI
        self.auth = auth(self)

        #DBPOOL对象
        if INI.DB_POOLS:
            self.PD = buildPoolDB(INI.DB_POOLS)
        st = self.st = Stat(obj=self)

        self.cmdmap = st.cmdmap
        self.maplk = st._maplk      #调度表锁


        self.setTask = st.setTask
        self.add_invoke = st.add_invoke
        self.loadFunction = st.loadFunction
        self.modReload = st.modReload

        #初始化调度表
        self.setTask(INI.INVOKER)

        #线程池在此
        self.tp = ThreadPool(MinPool, MaxPool)
        self.tp.start()

        self.auth.getInvoker()
        self.autoload()

    def showJob(self, cmd):
        try:
            self.maplk.acquire()
            if len(cmd) > 0:
                return self.printJob(cmd, self.cmdmap[cmd])
            else:
                buf = ''
                for k in self.cmdmap.keys():
                    buf += self.printJob(k, self.cmdmap[k])
                return buf
        except KeyError:
            return (65503, u'命令%s不存在' % cmd)
        finally:
            self.maplk.release()

    def printJob(self, cmd, job):
        cmd += ':\n'
        if len(job[2]) == 0:
            cmd += '\tNot invoked.\n'
        else:
            for obj, nouse in job[2]:
                if obj.starttime is None:
                    cmd += '\tLast Invoke(Not)\n'
                else:
                    cmd += '\tLast Invoke(%s)\n' % strftime("%Y-%m-%d %H:%M:%S", localtime(obj.starttime))

                if obj._lastTime is None:
                    cmd += '\tNext Invoke(Unknown)\n'
                else:
                    cmd += '\tNext invoke(%s)\n' % strftime("%Y-%m-%d %H:%M:%S", localtime(obj._lastTime))
        return (0, cmd)

    def autoload(self):
        """轮询调度表，自动装载具有'autoload'属性的作业
        """

        def cb(call):
            self.stop_invoke(call.cmd, call)

        try:
            self.maplk.acquire()
            for c, (s, objs, prop) in self.cmdmap.items():
                if 'autoload' in prop:
                    defer = self.start_invoke(c, {'factory':self}, None)
                    defer.addCallback(cb)
        finally:
            self.maplk.release()

    def del_invoke(self, cmd):
        """todo: 还要删除objmap，还要考虑正在运行的问题才能删掉模块和类的obj"""
        try:
            self.maplk.acquire()
            self.cmdmap.pop(cmd, None)
            #self.saveData(self.cmdmap, 'cmdmap')
        finally:
            self.maplk.release()

        try:
            self.modlk.acquire()
            for modname, (mod_object, mod_cmds) in self.modmap.items():
                for x in mod_cmds:
                    if x == cmd:
                        mod_cmds.remove(x)
                        break
                if len(mod_cmds) == 0:
                    self.modmap.pop(modname, None)    #应该不存在pop出None的情况，这里只是以防万一
        finally:
            self.modlk.release()

    def stop_invoke(self,cmd,caller):
        #caller ?
        job = self.st.getJob(cmd)
        msg = u'OK'
        if job:
            if job.running:
                job.stop()
                try:
                    self.maplk.acquire()
                    [s_mod, s_class, s_start, s_stop], invoke_obj, prop = self.cmdmap[cmd]
                    invoke_obj.remove(id(job))
                    self.cmdmap[cmd] = ([s_mod, s_class, s_start, s_stop], invoke_obj, prop)
                finally:
                    self.maplk.release()
                print 'stop task: %s success!'%cmd
                msg = u'停止任务：%s 成功！'%cmd
            else:
                print 'stop task: %s not run!'%cmd
                msg = u'停止任务：%s 没有运行！'%cmd

            self.st.delJob(cmd)
        else:
            print 'stop task: %s not found!'%cmd
            msg = u'停止任务：%s 未找到！'%cmd

        return (0, msg)

    def start_invoke(self, cmd, param, cronline):
        msg = ''
        try:
            self.maplk.acquire()
            [s_mod, s_class, s_start, s_stop], invoke_obj, prop = self.cmdmap[cmd]
            cron = self.makeCron(cronline)
            if len(invoke_obj) == 0 or cron is None:
                self.idInvoke += 1
                functions = self.loadFunction(s_mod, s_class, s_start, s_stop ,prop)
                if functions:
                    _start, _stop = functions
                    s_job = 'ScheduledCall(self.tp, self.idInvoke, cmd, _start, _stop, param)'
                    job = eval(s_job)
                    self.st.setJob(job,cmd)
                    print '%08d'%self.idInvoke,cmd,id(job)
                else:
                    print 'function load fail!'
                    raise IVKERROR,'调用函数：%s 或 %s 失败！'%( s_start, s_stop )
                    return

                s_defer = 'job.start(self.makeCron(cronline))'
                defer = eval(s_defer)
                invoke_obj.append(id(job))
                print
                self.cmdmap[cmd] = ([s_mod, s_class, s_start, s_stop], invoke_obj, prop)
                self.SD.cmdmap = self.cmdmap
                return defer
            else:#试图启动已经运行的定时任务
                raise IVKERROR,'试图启动已经运行的定时任务：%s!'%cmd
                return
        except KeyError:
            return None
        finally:
            self.maplk.release()

    def makeCron(self, cronline):
        if cronline is None or len(cronline) == 0:
            return None
        else:
            return CronSchedule(cronline)

    def process(self, cmd, type, param, cron):
        def cb(call):
            if call.schedule is None:               #无调度作业，需要立即析构call，否则有内存泄漏
                self.stop_invoke(cmd, call)
            return call.result

        if type == 'Stop':
            return self.stop_invoke(cmd, None)
        elif type == 'Show':
            return self.showJob(cmd)
        elif type == 'Reload':
            return self.modReload(cmd)
        else:
            defer = self.start_invoke(cmd, param, cron)
            if defer is None:
                return (65502, u'命令未定义')

            defer.addCallback(cb)
            if cron:
                return (0, u'任务：%s 启动成功！'%cmd)
            else:
                return defer

    def send(self, peer, data, cb, eb = None, param = None):
        """向peer发送data，成功后回调cb，失败后回调eb
        """
        def _eb(reason):
            print '*****', reason

        if not eb:
            eb = _eb
        addr, port = peer.split(':')
        f = SimpleFactory(data, cb, eb, param)
        f.connector = reactor.connectTCP(addr, int(port), f)


if __name__ == '__main__':
    factory = InvokerFactory(InvokerProtocol)
    reactor.listenTCP(8999, factory)
    reactor.run()


#coding:utf-8
import pickle, StringIO, threading, authxml
from invokerSHARE import TaskBase
from authorize import authorizeb
from xml.etree.ElementTree import fromstring

class auth(TaskBase):
    ao = authorizeb()
    usrd, usres, usrdlock = {}, {}, threading.RLock()

    def onInvoker(self, data, unuse):
        root = fromstring(data)
        buf = StringIO.StringIO()
        buf.write(root.text)
        self.ao.myInvoker = self.INI.AUTHLOCAL
        self.ao.allInvokers = pickle.loads(buf.getvalue())
        self.obj.bReady = True

    def getInvoker(self):
        self.obj.send(self.INI.AUTHCENTER, authxml.allsite(), self.onInvoker)

    def getUser(self, username, sysid):
        #用户外码->用户内码->用户资源
        try:
            self.usrdlock.acquire()
            usrid = self.usrd.get((username, int(sysid)), None)
            if usrid:
                return self.usres.get(usrid, None)
            else:
                return None
        finally:
            self.usrdlock.release()

    def authKey(self, *a, **kw):
        peer, bcd = eval(a[0]['peer']), a[0]['bcd']
        retcode, retmsg = self.ao.verifyKey(peer, bcd)
        if retcode == -1:
            retcode, retmsg = 1100, u'校验码无效'

        if retcode != 0:
            return pickle.dumps((retcode, retmsg))
        else:
            self.usrdlock.acquire()
            usres = self.usres.get(retmsg, None)
            self.usrdlock.release()
            return pickle.dumps(usres)

    def batch_process(self, cmds, authitems, ip, akey = None):
        idx, protocol = cmds[0], cmds[1]
        if idx >= len(cmds):
            return
        cmd, type, serial, param, cron = cmds[idx]
        if cmd in ['queryuser', 'allsite', 'authkey']:
            cmds[0] += 1
            protocol.process(cmd, type, serial, param, cron)
            return

        retcode, retmsg = self.authUser(authitems, ip, cmd, cmds)
        if retcode > 0:
            protocol.onMessage((retcode, retmsg), serial)
        elif retcode == 0:
            if akey is None:
                akey = self.ao.makeNextKey(ip, self.INI.AUTHLOCAL, retmsg)
            cmds[0] += 1
            protocol.process(cmd, type, serial, param, cron, akey)
            self.batch_process(cmds, authitems, ip)
        else: #waiting for request user's data
            pass

    def checkAuthorize(self, udata, authitems, ip, cmd):
        usr, res = udata
        return 0, usr[3]

    def onAuth(self, data, (cmds, authitems, ip)):
        protocol = cmds[1]
        root = fromstring(data)
        ret = int(root.attrib['ret'])
        if ret != 0:
            protocol.onMessage((ret, root.text), root.attrib['serial'])
        else:
            buf = StringIO.StringIO()
            buf.write(root.text)
            usr, res = pickle.loads(buf.getvalue())

            if usr is None:
                protocol.onMessage((1000, u'用户数据不存在1'), root.attrib['serial'])
            else:
                usrid = usr[3]
                self.usrdlock.acquire()
                self.usrd[(usr[1], usr[2])] = usrid
                if self.usres.has_key(usrid) == False:
                    self.usres[usrid] = (usr, res)
                self.usrdlock.release()
                self.batch_process(cmds, authitems, ip)

    def onRemoteAuth(self, data, (cmds, authitems, ip)):
        root = fromstring(data)
        buf = StringIO.StringIO()
        buf.write(root.text)
        retcode, retmsg = pickle.loads(buf.getvalue())

        if isinstance(retcode, int):    #远程认证出错了
            idx, protocol = cmds[0], cmds[1]
            cmd, type, serial, param, cron = cmds[idx]
            protocol.onMessage((retcode, retmsg), serial)
        else:                           #这就是用户的权限数据
            usrid = retcode[3]
            self.usrdlock.acquire()
            self.usrd[(retcode[1], retcode[2])] = usrid
            if self.usres.has_key(usrid) == False:
                self.usres[usrid] = (retcode, retmsg)
            self.usrdlock.release()

            authitems.pop('session', None)
            authitems['user'], authitems['sysid'] = retcode[1], retcode[2]
            self.batch_process(cmds, authitems, ip)

    def authUser(self, authitems, ip, cmd, param):
        retcode, retmsg = 1000, u'用户数据不存在2'
        if authitems.has_key('session'):
            retcode, retmsg = self.ao.verifyKey(ip, authitems['session'])
            if retcode == -1:           #其他站点的认证串
                self.obj.send(retmsg[0], authxml.authkey(ip, retmsg[1]), self.onRemoteAuth, None, (param, authitems, ip))
        elif authitems.has_key('user') and authitems.has_key('sysid'):
            udata = self.getUser(authitems['user'], authitems['sysid'])
            if udata is not None:       #已经取得用户信息
                retcode, retmsg = self.checkAuthorize(udata, authitems, ip, cmd)
            else:                       #没有用户信息，向中心认证站请求
                self.obj.send(self.INI.AUTHCENTER, authxml.queryuser(authitems['user'], authitems['sysid']), self.onAuth, None, (param, authitems, ip))
                retcode, retmsg = -1, u'Waiting me...'
        return retcode, retmsg

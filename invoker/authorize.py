
#coding:utf-8

import random, threading, time
from pyDes import *
from twisted.internet import reactor


myuuidseed = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ~!@#$%^&*()_+-=`[]{}|:";,./<>?)(+='
myuuidlen  = 7
bcdict = {'0': 0,
          '1': 1,
          '2': 2,
          '3': 3,
          '4': 4,
          '5': 5,
          '6': 6,
          '7': 7,
          '8': 8,
          '9': 9,
          'a': 10,
          'b': 11,
          'c': 12,
          'd': 13,
          'e': 14,
          'f': 15}

class authorizeb:
    uuidict = {}
    keycode = 'auth:>_<'
    uuidlck = threading.RLock()
    myInvoker, allInvokers = None, None

    def changeDeskey(self, key):
        self.uuidlck.acquire()
        self.keycode = key[0:8]
        self.uuidlck.release()

    def makeNextKey(self, peer, host, usrid, timeout = 120):
        peer = ''.join([e.zfill(3) for e in peer[0].split('.')])
        host, port = host.split(':')
        host = ''.join([e.zfill(3) for e in host.split('.')]) + '%05d' % int(port)
        tmp = ''
        for e in random.sample(myuuidseed, myuuidlen):
            tmp += e + peer[0:2]
            peer = peer[2:]
        tmp = [tmp, int(time.time()+timeout), usrid]

        try:
            self.uuidlck.acquire()
            tmp = des(self.keycode, CBC, "\0\0\0\0\0\0\0\0", pad=None, padmode=PAD_PKCS5).encrypt(str(tmp))
            bcd = ''
            for c in tmp:
                bcd += hex(ord(c)/16)[2:] + hex(ord(c)%16)[2:]
            self.uuidict[bcd] = self.keycode
        finally:
            self.uuidlck.release()

        reactor.callLater(timeout, self.getKey, tmp)
        return bcd+host

    def verifyKey(self, peer, bcd):
        oldbcd = bcd
        host = bcd[-17:]
        bcd = bcd[:-17]
        host = '%d.%d.%d.%d:%d' % (int(host[0:3].strip()), int(host[3:6].strip()), int(host[6:9].strip()), int(host[9:12].strip()), int(host[12:].strip()))

        if host == self.myInvoker:
            #本地校验key
            keycode = self.getKey(bcd)
            if keycode is None:
                return (1100, u'校验码无效1')

            tmp = ''
            for i in xrange(0, len(bcd)-1, 2):
                tmp += chr(bcdict[bcd[i]]*16+bcdict[bcd[i+1]])

            tmp = eval(des(keycode, CBC, "\0\0\0\0\0\0\0\0", pad=None, padmode=PAD_PKCS5).decrypt(tmp))
            if len(tmp[0]) != 19:
                return (1101, u'IP地址非法')

            addr = tmp[0][1:3]+tmp[0][4:6]+tmp[0][7:9]+tmp[0][10:12]+tmp[0][13:15]+tmp[0][16:18]
            if peer[0] != '%d.%d.%d.%d' % (int(addr[0:3]), int(addr[3:6]), int(addr[6:9]), int(addr[9:12])):
                return (1102, u'IP地址无效')

            if int(time.time()) > tmp[1]:
                return (1103, u'超时，请重新登录')

            return (0, tmp[2])      #返回用户内码

        elif host in self.allInvokers:
            #远程校验key
            return (-1, (host, oldbcd))

        else:
            return (1100, u'校验码无效2')

    def getKey(self, key):
        try:
            self.uuidlck.acquire()
            return self.uuidict.pop(key, None)
        finally:
            self.uuidlck.release()


def utest():
    ao = authorizeb()
    dd = ao.makeNextKey('127.3.0.1', '192.168.20.19', 1111)
    print dd
    print ao.verifyKey('127.3.0.1', dd)

if __name__ == '__main__':
    utest()
    reactor.run()


#coding:utf-8

import threading, StringIO, hashlib
from uuid import *
from xml.etree.ElementTree import ElementTree, Element, SubElement

uuid, reqserial, serialock = uuid4().hex, 0, threading.RLock()

def allsite():
    global uuid, reqserial, serialock

    root = ElementTree()
    req = Element('request')
    root._setroot(req)

    serialock.acquire()
    reqserial += 1
    serial = '%s.%d' % (uuid, reqserial)
    serialock.release()

    item = Element('auth')
    req.append(item)
    item = Element('command', {'flag':'', 'cmd':'allsite', 'serial':serial})
    req.append(item)

    out = StringIO.StringIO()
    root.write(out, 'utf-8')
    s = out.getvalue().lower()
    out.close()

    m = hashlib.md5()
    m.update(s.strip('\r\n'))
    buf = m.hexdigest()+s
    return buf

def queryuser(username, sysid):
    global uuid, reqserial, serialock

    root = ElementTree()
    req = Element('request')
    root._setroot(req)

    serialock.acquire()
    reqserial += 1
    serial = '%s.%d' % (uuid, reqserial)
    serialock.release()

    item = Element('auth')
    req.append(item)
    item = Element('command', {'flag':'', 'cmd':'queryuser', 'serial':serial})
    req.append(item)
    SubElement(item, 'param', {'name':'user'}).text = username
    SubElement(item, 'param', {'name':'sysid'}).text = sysid

    out = StringIO.StringIO()
    root.write(out, 'utf-8')
    s = out.getvalue().lower()
    out.close()

    m = hashlib.md5()
    m.update(s.strip('\r\n'))
    buf = m.hexdigest()+s
    return buf

def authkey(peer, bcd):
    global uuid, reqserial, serialock

    root = ElementTree()
    req = Element('request')
    root._setroot(req)

    serialock.acquire()
    reqserial += 1
    serial = '%s.%d' % (uuid, reqserial)
    serialock.release()

    item = Element('auth')
    req.append(item)
    item = Element('command', {'flag':'', 'cmd':'authkey', 'serial':serial})
    req.append(item)
    SubElement(item, 'param', {'name':'peer'}).text = str(peer)
    SubElement(item, 'param', {'name':'bcd'}).text = bcd

    out = StringIO.StringIO()
    root.write(out, 'utf-8')
    s = out.getvalue().lower()
    out.close()

    m = hashlib.md5()
    m.update(s.strip('\r\n'))
    buf = m.hexdigest()+s
    return buf


#coding:utf-8

import socket, hashlib, time, StringIO
from xml.dom.minidom import parseString
from xml.etree.ElementTree import ElementTree, Element, SubElement, fromstring

invoker_addr = ('127.0.0.1', 8999)
akey = ''
serial = 0

#内部业务 req 'queryuser', user='xinl', sysid='19'
#req 'new', {'user':'xinl', 'sysid':'19'}

def makeRequest(command, auth = {}, flag = '', **kw):
    global serial, akey

    root = ElementTree()
    req = Element('request')
    root._setroot(req)

    if len(auth):
        item = Element('auth')
        req.append(item)
        for k, v in auth.iteritems():
            SubElement(item, 'option', {'name':k}).text = v
    elif len(akey):
        item = Element('auth')
        req.append(item)
        SubElement(item, 'option', {'name':'session'}).text = akey
    else:
        print u'请求无认证信息'
        return None

    item = Element('command', {'flag':flag, 'cmd':command, 'serial':str(serial)})
    serial += 1
    req.append(item)
    for k, v in kw.iteritems():
        SubElement(item, 'param', {'name':k}).text = v

    out = StringIO.StringIO()
    root.write(out, 'utf-8')
    s = out.getvalue().lower()
    out.close()

    m = hashlib.md5()
    m.update(s.strip('\r\n'))
    buf = m.hexdigest()+s
    print buf
    return buf

def request(buf):
    global akey
    s = socket.socket()
    s.connect(invoker_addr)
    s.send(buf)

    ans = ''
    while True:
        ans += s.recv(1024*64)
        if ans.rfind('</answer>') == len(ans)-len('</answer>'):
            break
    s.close()

    _md5 = ans[0:32]
    ans = ans[32:]
    m = hashlib.md5()
    m.update(ans)
    if m.hexdigest() != _md5:
        return (serial+1, u'MD5校验失败')

    dom = parseString(ans)
    root = dom.documentElement
    no = root.getAttribute('serial')
    akey = root.getAttribute('auth')
    data = root.childNodes[0].data
    return (no, akey, data)


def mainloop():
    global invoker_addr, akey
    while True:
        in_buffer = raw_input((u'当前服务器%s，请输入指令:\n' % str(invoker_addr)).encode('gbk'))
        command = in_buffer.lower().split(' ', 1)

        if command[0] == 'quit':
            break
        elif command[0] == 'setip':
            command = command[1].split(':')
            invoker_addr = (command[0], int(command[1]))
        elif command[0] == 'req':
            cmdbuf = 'makeRequest('+command[1]+')'
            req = eval(cmdbuf)
            if req is None:
                continue

            no, akey, ans = request(req)
            print 'Serial %s:' % no, '--------->'
            print 'Key:', akey
            print ans
        else:
            print u'setip %ip:%port ----------------------------- 设置invoker地址'
            print u'req %cmd[,auth={%auth}][,flag=%flag][,**kw] - 向当前invoker发送请求'
            print u'quit ---------------------------------------- 退出测试程序'
        print



def localtest():
    req = eval("makeRequest('new', auth={'user':'xinl', 'sysid':'19'})")
    no, akey, ans = request(req)
    print '--------------------------------------------------------'
    print 'Serial %s:' % no, '--------->'
    print 'Key:', akey
    print ans
    print '--------------------------------------------------------'
    req = eval("makeRequest('new')")
    no, akey, ans = request(req)
    print 'Serial %s:' % no, '--------->'
    print 'Key:', akey
    print ans
    print '--------------------------------------------------------'

def multitest():
    import time
    global invoker_addr
    addr1, addr2 = ('192.168.48.15', 8999), ('192.168.11.25', 8999)

    invoker_addr = addr2
    req = eval("makeRequest('new', auth={'user':'xinl', 'sysid':'19'})")
    no, akey, ans = request(req)
    print '--------------------------------------------------------'
    print 'Serial %s:' % no, '--------->'
    print 'Key:', akey
    print ans
    print '--------------------------------------------------------'

    invoker_addr = addr1
    req = eval("makeRequest('new')")
    no, akey, ans = request(req)
    print 'Serial %s:' % no, '--------->'
    print 'Key:', akey
    print ans
    print '--------------------------------------------------------'

if __name__ == '__main__':
    multitest()


#coding:utf-8

from invoker.invoker import InvokerProtocol,InvokerFactory
from twisted.internet import reactor

from SHARE import INI


if __name__ == '__main__':
    #try:
        factory = InvokerFactory(InvokerProtocol)
        reactor.listenTCP(INI.PORT, factory)
        reactor.run()
    #except :
    #    print 'Invaker maybe running!'



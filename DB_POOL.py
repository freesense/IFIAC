
#coding:utf-8

import pymssql, threading, sys
from twisted.python.failure import Failure
from twisted.internet import defer

class PoolDB:
    def __init__(self):
        self.dconn = {}
        self.dlock = threading.RLock()

    def buildpool(self, tag, sql_host, sql_user, sql_pwd, sql_db, num = 5):
        try:
            self.dlock.acquire()
            self.dconn[tag] = []
            for x in xrange(num):
                conn = pymssql.connect(host = sql_host,
                                       user = sql_user,
                                       password = sql_pwd,
                                       database = sql_db)
                cur = conn.cursor()
                self.dconn[tag].append(cur)
            return True
        except:
            self.dconn.pop(tag, None)
            print u'连接数据库[%s.%s]失败' % (sql_host, sql_db)
            return False
        finally:
            self.dlock.release()

    def errback(self, failure):
        print failure

    def run(self, tag, sql, cb = None, eb = None):
        cur = None
        if eb is None:
            eb = self.errback

        try:
            self.dlock.acquire()
            curs = self.dconn[tag]
            cur = curs.pop()
        except KeyError:
            eb(Failure('Tag not found', 1))
            return
        except IndexError:
            eb(Failure('No connection', 2))
            return
        except:
            eb(Failure(sys.exc_info()))
            return
        finally:
            self.dlock.release()

        d = defer.execute(self._exec_sql, tag, cur, sql)
        if cb is not None:
            d.addCallback(cb)
        d.addErrback(eb)

    def _exec_sql(self, tag, cur, sql):
        try:
            import time
            time.sleep(10)
            cur.execute(sql)
            data = cur.fetchall()
            print type(data)
            return data
        except:
            return Failure(sys.exc_info())
        finally:
            try:
                self.dlock.acquire()
                self.dconn[tag].append(cur)
            finally:
                self.dlock.release()


def cb(result):
    print '1:', type(result)

def eb(failure):
    print '2:', failure

if __name__ == '__main__':
    p = PoolDB()
    
    p.buildpool(1126, '192.168.11.26', 'xinl', 'xinl', 'pd_10_web')
    
##    print u'连接池建立'
    p.run(1126, 'select * from QOT_D_FACT_SIXT', cb, eb)
    print 11122333
    p.run(1126, 'select * from QOT_D_FACT_SIXT', cb, eb)

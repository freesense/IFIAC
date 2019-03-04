
#coding:utf-8

#已知问题
#select * from testname;insert into testname values('3ed', 2);select * from testname；
#第二条insert语句返回的影响行数不正确，返回的是第一条select语句的影响行数
"""
select * from ddd
select * from eee

delete ddd
delete eee

insert into ddd(f1,f2,f3,id) values('1','2','3',1)

if exists (select id from ddd where f1='1')
 update ddd set f1='2',f2='2',f3='3',id=2 where f1='1'
else
 insert into ddd(f1,f2,f3,id) values('3','4','5',3)
"""
import threading, sys, re, time
import adodbapi
from twisted.python.failure import Failure
from twisted.internet import defer
from twisted.python.threadpool import ThreadPool


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

#定义ado默认行为
adodbapi.defaultIsolationLevel = adodbapi.adXactRepeatableRead
adodbapi.defaultCursorLocation = adodbapi.adUseClient

#线程池的最大最小并行线程数量
MaxPool = 50
MinPool = 5

#连接池的空闲比
FreePoolRate = 0.5

dbtypemap = {3   : 'int',
             6   : 'money',
             205 : 'image',
             5   : 'float',
             131 : 'numeric',
             135 : 'datetime',
             129 : 'char',
             20  : 'bigint',
             202 : 'nvarchar',
             2   : 'smallint',
             128 : 'binary',
             200 : 'varchar',
             131 : 'decimal',
             17  : 'tinyint',
             201 : 'text',
             4   : 'real',
             11  : 'bit',
             203 : 'ntext',
             130 : 'nchar',
             135 : 'smalldatetime',
             72  : 'uniqueidentifier',
             128 : 'timestamp',
             12  : 'sql_variant',
             6   : 'smallmoney',
             204 : 'varbinary'
            }


class row:
    def __init__(self, fields, rowdata):
        self.rowdata = rowdata
        self.fields = fields

    def __getattr__(self, key):
        try:
            pos = self.fields[key.upper()]['pos']
            return self.rowdata[pos]
        except:
            print 'row name:%s not found!' % key.upper()

    def __call__(self):
        return self.rowdata

class DBERROR(BaseException):pass

class dbrs:
    def __init__(self, description, data):
        self.fields = {}
        self.rows = data
        pos = 0
        for field in description:
            fd = {}
            name, fd['type'], fd['display_size'], fd['internal_size'], fd['precision'], fd['scale'], fd['null_allowed'] = field
            fd['type'] = dbtypemap.get(fd['type'], 'unknown')
            fd['pos'] = pos
            pos += 1
            self.fields[name.upper()] = fd

    def __iter__(self):
        for item in self.rows:
            yield row(self.fields, item)

    def __repr__(self):
        return '<Fields: ' + str(self.fields) + ', Rows: ' + str(self.rows) + '>'

    def __len__(self):
        return len(self.rows)

def ParsePoolDBError(failure):
    import urllib
    f = failure.getErrorMessage()
    f = urllib.unquote(f.replace('\\\\x', '%'))
    f = f.replace('\\n', '\n')
    f = f.replace('\\\\', '\\')
    f = f.replace('\\\'', '\'')
    return f

class PoolDB:
    def __init__(self, ConnectionString, failback = None, minConn = 5, maxConn = 10):
        self.dconn = []
        self.dlock = threading.RLock()
        self.pattern = re.compile(r'.*\bdelete\b.*|.*\binsert\b.*|.*\bupdate\b.*|.*\bexec\b.*', re.IGNORECASE)
        self.ConnectionString = ConnectionString
        self.failback = failback

        self.minc, self.maxc, self.curc, self.cv = minConn, maxConn, 0, threading.Condition(self.dlock)
        self.dbready = self.buildpool(self.minc)

        #建立缓冲区，缓冲内容为(defer, request, params)
        self.reqbuffer = []
        self.block = threading.RLock()

        #线程池在此
        self.tp = ThreadPool(MinPool, MaxPool)
        self.tp.start()

    def __del__(self):
        self.cv.acquire()
        self.minc = 0
        for conn in self.dconn:
            conn.close()
            self.curc -= 1
        while self.curc > 0:
            self.cv.wait()
        self.cv.release()
        self.tp.stop()

    def setMaxConnection(self, maxConn):
        try:
            self.dlock.acquire()
            if maxConn > self.maxc:
                self.maxc = maxConn
        finally:
            self.dlock.release()

    def buildpool(self, num = 2):
        result = False
        try:
            self.dlock.acquire()
            for x in xrange(num):
                conn = adodbapi.connect(self.ConnectionString)
                if conn is not None:
                    self.dconn.append(conn)
                    self.curc += 1
                else:
                    print u'连接数据库[%s]失败' % self.ConnectionString
                    return #False
            result = True
        except:
            print u'连接数据库[%s]失败' % self.ConnectionString
        finally:
            self.dlock.release()
        return result

    def errback_print(self, failure, **kw):
        print '----- PoolDB Error -----'
        if kw:
            print kw
        print ParsePoolDBError(failure)
        print '------------------------'

    def errback_retry(self, failure, **kw):
        print ParsePoolDBError(failure)
        time.sleep(2)
        self.run(kw['sql'], kw['param'], kw['cb'], kw['eb'], kw['obj'])

    def run(self, sql, params=None, cb=None, eb=None, obj=None, d=None):
        def onResult(success, result):
            try:
                d, r = result
            except TypeError:
                print '>>>', sql, params, '>>>', result
            if success:
                d.callback(r)
            else:
                d.errback(r)

        conn = None
        buildnum = 0

        if d is None:
            d = defer.Deferred()
            if cb is not None:
                d.addCallback(cb, sql=sql, param=params, cb=cb, eb=eb, obj=obj, d=d)
            if eb is None:
                eb = self.errback_retry
            d.addErrback(eb, sql=sql, param=params, cb=cb, eb=eb, obj=obj, d=d)
            d.addCallback(self._next_sql)
            d.addErrback(self._next_sql)

        try:
            self.dlock.acquire()
            conn = self.dconn.pop()
            if len(self.dconn) < 2 and self.curc < self.maxc:
                buildnum = min(2, self.maxc - self.curc)
        except IndexError:
            self.block.acquire()
            self.reqbuffer.append((d, sql, params))
            self.block.release()
            return
        except:
            d.errback(sys.exc_info())
            return
        finally:
            self.dlock.release()

        self.tp.callInThreadWithCallback(onResult, self._exec_sql, d, conn, sql, params)

        if buildnum > 0:
            self.buildpool(buildnum)

    def _exec_sql(self, d, conn, sql, params):
        try:
            fail = None
            cur = conn.cursor()

            try:
                cur.execute(sql, params)
            except:
                if self.pattern.search(sql) is not None:
                    conn.rollback()
                fail = Failure(sys.exc_info())
                return d, fail
            else:
                if self.pattern.search(sql) is not None:
                    conn.commit()

            Flag, rs = True, []
            while Flag is not None:
                try:
                    data = cur.fetchall()
                    rs.append(dbrs(cur.description, data))
                except:
                    rs.append(cur.rowcount)
                Flag = cur.nextset()
            return d, rs
        finally:
            cur.close()
            flag, fbret = False, 0

            if fail and self.failback:
                fbret = self.failback(fail)
            if fbret:
                cnt = 0
                while True:
                    cnt += 1
                    print u'试图重连数据库...', cnt
                    if self.buildpool(fbret):
                        break

            self.dlock.acquire()
            if fbret > 0:
                flag = True
            elif self.minc == 0:
                flag = True
            elif self.curc > self.minc and len(self.dconn)/float(self.curc) >= FreePoolRate:
                flag = True

            if flag == True:
                conn.close()
                self.curc -= 1
                if self.minc == 0:
                    self.cv.notify()
            else:
                self.dconn.append(conn)
            self.dlock.release()

    def _next_sql(self, *argv):
        try:
            self.block.acquire()
            defer, sql, params = self.reqbuffer.pop(0)
        except IndexError:
            self.block.release()
            return False
        else:
            self.block.release()
            self.run(sql, params, d=defer)
            return True

def cb(result, **kw):
    print result

class dbBASE:
    _sqlid = "declare @tt int;exec %sGetMaxID ?, @tt output;select @tt"

    def getSqlId(self):
        s = '..%s'%self.table
        dbname = s.split('..')[-2]
        if dbname:
            sql = self._sqlid%('%s..'%dbname)
        else:
            sql = self._sqlid%''
        return sql

    def queryid(self):
        self.p.run(self.sqlid, [self.table], cb = self.onidok, eb = self.errback, obj = self)

    def __del__(self):
        print u'表[%s]更新完成，共插入%d/%d条记录' % (self.table, self.success, len(self.rows))

    def replaceString(self, s, kw=None):
        if not kw:
            kw = {"'~~~":'',"~~~'":''}
        for k,v in kw.items():
            s = s.replace(k,v)
        return s

    def onrowok(self, result, *args, **kw):
        if isinstance(result, Failure):
            print u'>>> 修改数据出错[%s]:' % (self.table), self.rows[self.idx]
        elif isinstance(result[0], int):
            self.success += result[0]
        if self.idx+1 < len(self.rows):
            self.queryid()

class _batch_insert(dbBASE):
    #_sqlid = "declare @tt int;exec %sGetMaxID ?, @tt output;select @tt"
    def __init__(self, p, sql, table, rows, eb = None):
        self.p = p
        self.sql = sql
        self.table = table
        self.sqlid = self.getSqlId()
        self.rows = rows
        self.eb = eb
        self.idx = -1
        self.success = 0

#    def getSqlId(self):
#        s = '..%s'%self.table
#        dbname = s.split('..')[-2]
#        if dbname:
#            sql = self._sqlid%('%s..'%dbname)
#        else:
#            sql = self._sqlid
#        return sql
#
#    def __del__(self):
#        print u'表[%s]更新完成，共插入%d/%d条记录' % (self.table, self.success, len(self.rows))
#
#    def queryid(self):
#        self.p.run(self.sqlid, [self.table], cb = self.onidok, eb = self.eb, obj = self)

    def onidok(self, result, *args, **kw):
        tid = result[1].rows[0][0]

        self.idx += 1
        #self.rows[self.idx].append(tid)

        v = self.rows[self.idx]
        if isinstance(self.rows[self.idx],list):
            v = tuple(self.rows[self.idx])
        v += (tid,)

        sql = self.sql%v

        self.p.run(sql, cb = self.onrowok, eb = self.errback, obj = self)
        #self.p.run(self.sql, self.rows[self.idx], cb = self.onrowok, eb = self.errback, obj = self)

#    def onrowok(self, result, *args, **kw):
#        if isinstance(result, Failure):
#            print u'>>> 插入数据出错[%s]:' % (self.table), self.rows[self.idx]
#        elif isinstance(result[0], int):
#            self.success += result[0]
#        if self.idx+1 < len(self.rows):
#            self.queryid()

def batch_insert(p, params, eb = None):
    for table, define in params.iteritems():
        if not define:
            continue
        if not define['field'] or not define['data']:
            continue

        sql = "insert into " + table + "("
        for field in define['field']:
            sql += field + ','
        sql += 'id) values(' + '?,'*len(define['field']) + '?)'

        sql = sql.replace('?',"'%s'")
        bt = _batch_insert(p, sql, table, define['data'], eb)
        bt.queryid()


class _batch_update(dbBASE):
    #sqlid = "declare @tt int;exec GetMaxID ?, @tt output;select @tt"
    def __init__(self, p, sql, table, rows, check, append, eb = None):
        self.p = p
        self.sql = sql
        self.table = table
        self.rows = rows
        self.sqlid = self.getSqlId()
        #print 11111111111111111,self.sqlid
        self.check = check
        self.append = append
        self.eb = eb
        self.idx = -1
        self.success = 0

    def __del__(self):
        print u'表[%s]更新完成，共影响%d/%d条记录' % (self.table, self.success, len(self.rows))

    def queryid(self):
        self.p.run(self.sqlid, [self.table], cb = self.onidok, eb = self.eb, obj = self)

    def onidok(self, result, *args, **kw):
        """
        if exists (select id from ddd where f1=? and f2=?) update ddd set f1=?,f2=?,f3=? where f1=? and f2=? else insert into ddd(f1,f2,f3,id) values(?,?,?,?)
        """
        self.idx += 1
        tid = result[1].rows[0][0]
        rows = self.rows[self.idx]
        v, v_check = [], []
        for n in self.check:
            v_check.append(rows[n])
        for n,row in enumerate(rows):
            v.append(row)
            if n in self.append:#append 需要两个值
                v.append(row)
        v = v_check + v + v_check
        for n,row in enumerate(rows):
            if row and n in self.append:
                v.append("~~~convert(varchar(20),getdate(),121)+' '+'%s'~~~"%row)
            else:
                v.append(row)
        #v += rows

##        v += self.rows[self.idx]
##        v *= 2
        v.append(tid)

        sql = self.sql%tuple(v)
        sql = self.replaceString(sql)
#        print sql
        self.p.run(sql, cb = self.onrowok, eb = self.errback, obj = self)

        #self.p.run(self.sql, v, cb = self.onrowok, eb = self.errback, obj = self)

    def onrowok(self, result, *args, **kw):
        if isinstance(result, Failure):
            print u'>>> 修改数据出错[%s]:' % (self.table), self.rows[self.idx]
        elif isinstance(result[0], int):
            self.success += result[0]
        if self.idx+1 < len(self.rows):
            self.queryid()


def batch_update(p, params, eb = None):

    for table, define in params.iteritems():
        if not define or not define.get('field') or not define.get('data')or not define.get('keys'):
            continue
        for key in define:
            if key not in ['data']:
                define[key] = [e.upper() for e in define[key]]

        check = [define['field'].index(e) for e in define['keys']]
        append = [define['field'].index(e) for e in define['append']]

        sql = "if exists (select id from " + table + " where "
        for key in define['keys']:
            sql += key + '=? and '
        sql = sql.rstrip('and ') + ') update ' + table + ' set '

        for field in define['field']:
            if define.get('append') and field in define['append']:
                sql += field + '''=case when Datalength(?)>0 then convert(varchar(max),[Remark])+'\r\n'+convert(varchar(20),getdate(),121)+' '+? else [Remark] end, '''
                #sql += field + '=convert(varchar(max),' + field + ')+?,'
            else:
                sql += field + '=?,'

        sql += ' mdate=getdate() where '
        for key in define['keys']:
            sql += key + '=? and '
        sql = sql.rstrip('and ') + ' else insert into ' + table + '('
        for field in define['field']:
            sql += field + ','
        sql += 'id) values(' + '?,'*len(define['field']) + '?)'

        sql = sql.replace('?',"'%s'")
        bt = _batch_update(p, sql, table, define['data'], check, append, eb)
        bt.queryid()

def failback_reconnect(failure):
    f = ParsePoolDBError(failure)
    if f.find(chgCoding('连接失败')) != -1 or f.find(chgCoding('一般性网络错误')) != -1:
        return 1
    else:
        return 0

if __name__ == '__main__':
    #p = PoolDB('Provider=SQLOLEDB.1;Server=192.168.11.29;uid=test_fanp;pwd=test_fanp*#dbr;database=test2_basedb_work')
    p = PoolDB('Provider=SQLOLEDB.1;Server=192.168.48.13;uid=test;pwd=testtest;database=test', failback_reconnect)
    print u'连接池OK'
    time.sleep(60)
    #t = u'汉字'
    #d = '2000-01-01 11:11:11'
    #select * from ddd;insert into ddd values('d1','d2','d3',1);
    sql = """
    select * from ddd;
    """
    p.run(sql, cb=cb)
    #p.run("insert into testname(varchar, int) values('aaz', 2);", cb)
    #p.run("delete from testname", cb)
    #p.run("select * from testname", cb=cb, obj='3ed')
    #p.run("select * from testname;insert into testname(varchar, int) values('asds', 2);", cb)
    #p.run("select * from testname;", cb)
    #p.run("insert into testname(varchar, int) values('3ed', 2);insert into testname(varchar, int) values('gvbn', 2);", cb)
    #p.run("select 1; select 2;", cb=cb, obj='wsard')
    #p.run("declare @tt int; exec GetMaxID ddd, @tt output; select @tt", cb)
    #p.run("declare @tt int;exec GetMaxID 'ddd', @tt output;select @tt", cb)
    #d = {'ddd':{'field':['f1','f2','f3'], 'data':[[0,1,2],[1,2,3]]},
    #     'eee':{'field':['a','b'], 'data':[['qq','ww'],['fvf','gbh'],['op[','...']]}}
    #d = {'ddd':{'field':['f1','f2','f3'], 'data':[(0,1,2),(1,2,3)]},
    #     'eee':{'field':['a','b'], 'data':[('qq','ww'),('fvf','gbh'),('op[','...')]}}
    #d = {'ddd':{'field':['f1','f2','f3'],'keys':['f1','f2'],'data':[('aaa',1,2),(1,2,3),(1,3,3),(1,2,4)]}}
    #d = {'ddd':{'field':['f1','f2','f3'],'keys':['f1','f2'],'data':[[aaa,1,2],[1,2,3],[1,3,3],[1,2,4]]}}
    #batch_update(p, d)
    #d = {'file_attribute':{'data':[('3d94bfedf3408f944541db383cc67f8b','D:\\work\\Python\\source\\Ann\\20091014\\a\\0000.pdf',\
    #                                'b6b8bb0f-bfb1-11de-899d-0022fa95ff22','\\ANN\\20091023\\b6b8bb0f-bfb1-11de-899d-0022fa95ff22.pdf',1,10,'xcc')],
    #    'field':  #需要写入数据表的字段
    #        ['MD5Code','SourceName', 'UUID', 'NewName', 'TStatus','Process', 'Remark'],
    #    'keys': #修改记录的查询字段
    #        ['UUID'],
    #    'append':['remark']
    #    }}
##    print d
    #batch_insert(p, d)
    #batch_update(p, d)
    del p

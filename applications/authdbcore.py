
#coding:utf-8
import pickle
from invokerSHARE import TaskBase

client_address = []

class authdbcore(TaskBase):
    def getUsrAuth(self, *a, **kw):     #获得用户状态，到期日期，认证模式，用户自定义数据以及用户可访问的资源信息
        global client_address
        self.callbackend = a[0]['async_callback_end']
        if a[0]['peer_address'] not in client_address:
            client_address.append(a[0]['peer_address'])

        sql = "select a.verify as vgroup, b.usrid, b.class as nclass, b.status as nstatus, c.status as wstatus, c.overduedate, c.vdata1,c.vdata2,c.vdata3, e.* from tn_group a,tn_user b,tw_user c,tn_usright d,tn_resource e where a.groupid=b.groupid and b.usrid=c.usrid and d.groupid=a.groupid and d.resid=e.resid and c.usrname='%s' and c.sysid=%s" % (a[0]['user'], a[0]['sysid'])
        self.obj.PD.authdb.run(sql, cb=self.onUserSqlReturned, obj=(a[0]['user'], int(a[0]['sysid'])))

    def getAllInvoker(self, *a, **kw):
        return pickle.dumps(self.INI.ALLINVOKER)

    def __del__(self):
        print 'del authdbcore'

    def onUserSqlReturned(self, result, **kw):
        if len(result) == 0:
            print '无用户'
            return

        self.user, self.res = None, []
        for row in result[0]:
            if self.user is None:
                self.user = ([row.vgroup], kw['obj'][0], kw['obj'][1], row.usrid, row.nclass, row.nstatus, row.wstatus, row.overduedate, row.vdata1, row.vdata2, row.vdata3)
            elif row.vgroup not in self.user[0]:
                self.user[0].append(row.vgroup)

            if row.resid not in [resid for resid,type,name,unuse,unuse in self.res]:
                self.res.append((row.resid, row.restype, row.resname, row.resclass, row.verify))

        s = pickle.dumps((self.user, self.res))
        self.callbackend(s)

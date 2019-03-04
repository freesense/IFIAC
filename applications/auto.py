
#coding:utf-8

from invokerSHARE import TaskBase

class autoload(TaskBase):
    def start(self, *t, **d):
        #f = t[1]['factory']
        f = self.obj
        #print '>>>>>>>>>>>', f.PD
        tasklist = {}

        for task in f.INI.AUTO:
            cmd, ivk, cron = task[:3]
            prop = dict()
            if 'share' in task[-1]:
                prop['share'] = 1

            tasklist[cmd] = cron
            f.add_invoke(cmd, ivk, prop)
        for x in tasklist:
            f.start_invoke(x, {}, tasklist[x])

    def stop(self, *t, **d):
        print 'auto stopped.'





# -*- coding: UTF-8 -*-
##############################################################################
#
# Copyright (c) Investoday Financial Information LTD.
#        File:  DB_TOOLS.py
#      Author:  Frank Fan
# Start  Date:  2009.09.17
# Last modify:
#
##############################################################################

"""数据库引擎：DB_TOOLS.py：
          一次性批量接收sql指令，通过连接池多线程执行，并用cb返回结果。
"""

__version__='$Revision: 1.00 $'[11:-2]


class dbPools:
    """动态提供修改连接池数量，由min,max提供。调用按需生成连接，当可用比（可用/总数）大于指定的数值（50%）时，动态关闭空闲连接。
    
                    初始化参数：db server,username,password,default_db,minnum,maxnum
                    实现方法：
                       
                       getConn()从连接池中获得数据库连接
                       putConn()返回数据库连接给连接池
                
                       setPoolNum(min,max)
                       creatConn(num)生成指定num数据库连接
                       closeConn(num)关闭指定num数据库连接
                       creat()生成dbpool
                       close()关闭dbpool
    """
    
    def __init__(self, DSN, minnum = 5,maxnum = 10):
        """DSN = (db server,username,password,default_db)
        """
        pass
    
    def getConn(self):
        """getConn()从连接池中获得数据库连接
        """
        pass
    
    def putConn(self):
        """putConn()返回数据库连接给连接池
        """
        pass
           
    def setPoolNum(self):
        """setPoolNum(min,max)
        """
        pass
     
    def creatConn(self,num):
        """creatConn(num)生成指定num数据库连接
        """
        pass
    
    def closeConn(self,num):
        """closeConn(num)关闭指定num数据库连接
        """
        pass
    
    def close(self,num):
        """close()关闭dbpool 
        """
        pass
       
                           
    
   
class dbUtility:
    """提供数据库应用封装，由提供数据生成相应的sql,执行，并返回结果。
    """
    def __init__(self,conn):
        self.conn = conn    #数据库连接
        pass
    def select(self,sql):
        pass
    def delete(self,sql):
        pass
    def update(self,sql):
        pass
    def insert(self,sql):
        pass
    def fetchdata(self,cur):
        pass
    def fetchall(self,cur):
        pass
    
    def insertData(self,data = dict):
        pass
    
    def select_for_grid(self,sql,pageNo=1,select_size=10):
        pass
    
    
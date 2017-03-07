#!/usr/bin/env python

import MySQLdb

class MYDB():
    def __init__(self):
        self.db = MySQLdb.connect(host="172.16.12.98",  # your host, usually localhost
                                  user="intadmin",      # your username
                                  passwd="xiaolou770",  # your password
                                  db="int_db")          # name of the data base
        self.cur = self.db.cursor()

    def commit(self):
        self.db.commit()

    def executeAndCommit(self,cmd):
        self.cur.execute(cmd)
        self.db.commit()

    def execute(self, cmd):
        self.cur.execute(cmd)

    def executeAndFetch(self, cmd):
        self.cur.execute(cmd)
        return self.cur.fetchall()

    def printall(self, cmd):
        self.execute(cmd)
        for row in self.cur.fetchall() :
            print row

    def close(self):
        self.cur.close()
        self.db.close()


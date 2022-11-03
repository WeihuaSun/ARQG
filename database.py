import re
import psycopg2
DATABASE_URL = "postgres://postgres:1@192.168.31.102:21432/postgres"
reg_cost = r"cost=([0-9]+\.[0-9]+)\.\.([0-9]+\.[0-9]+)"
reg_card = r"rows=([0-9]+)"


class Database:
    def __init__(self, DATABASE_URL):
        self.conn = psycopg2.connect(DATABASE_URL)
        self.conn.autocommit = True
        self.cur = self.conn.cursor()

    def run(self, sql):
        try:
            self.cur.execute(sql)
            rows = self.cur.fetchall()
            return rows
        except:
            return None
    def sample(self,col,table,percentage=0.001):
        return self.run("select {} from {} TABLESAMPLE bernoulli({});".format(col,table,percentage))
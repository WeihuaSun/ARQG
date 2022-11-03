import pickle
import psycopg2
import math
import random
import sys
from collections import OrderedDict
import re
import os
from typing import Dict, NamedTuple, Optional, Tuple, Any, List
import constants
from database import Database
class DataProcess():
    def __init__(self):
        #self.hash = Hash()
        pass

    def rebuild(self, sql):
        reg_selectbasic = r"(SELECT\sCOUNT\(\*\)\s)"
        reg_join = r"([a-z_A-Z]+)\.([a-z_A-Z]+)=([a-zA-Z]+)\.([a-z_A-Z]+)"
        reg_pred = r"([a-z_A-Z]+)\.([a-z_A-Z]+)(=|>|<)([0-9]+)"
        reg_sql = r"{}WHERE\s(.*);".format(reg_selectbasic)
        vm = re.search(reg_sql, sql)
        if vm == None:
            return None
        selects = vm.group(1)
        wheres = vm.group(2)
        tables = set()
        for m in re.finditer(reg_join, wheres):
            tables.add(m.group(1))
            tables.add(m.group(3))
           
        for m in re.finditer(reg_pred, wheres):
            predicate = m.group(0)
            t, c, op, key = m.group(1), m.group(2), m.group(3), m.group(4)
            tables.add(t)
            col = "{}.{}".format(t, c)
            key = int(key)
            #############改这里####################
            #hash_val = self.hash.value_(col, key) 
            hash_val = 1000
            new = "{}.{}{}{}".format(t, c, op, hash_val)
            wheres = wheres.replace(predicate, new)
            
        sql = selects+"FROM "
        ta = tables.pop()
        sql = sql + \
            "{}".format(ta)
        for t in tables:
            sql = sql + \
                ",{}".format(t)
        sql = sql + " WHERE " + wheres + ";"
        return sql


class Values(NamedTuple):
    values: Dict[str, Optional[set]]#column:value


class Cardinality():
    # col,val,op,card
    card: Dict[str, Optional[Dict[int, Dict[str, int]]]]
  
class Hash:
    # 每一列的值进行hash分桶，分为HASH_NUM个桶
    hash_bucket: Dict[str, Dict[int, Optional[List[int]]]]
    col_info: Dict[str, Optional[Tuple[int, int]]]
    hash_num: Dict[str, int]

    def __init__(self):
        self.hash_bucket = OrderedDict.fromkeys(constants.colset, None)
        self.col_info = OrderedDict.fromkeys(constants.colset, None)
        self.hash_num = OrderedDict.fromkeys(constants.colset, None)
        values = self.getvalues()
        for col in constants.colset:
            if values[col] is not None:
                #############改这里####################
                minval = int(min(values[col]))#这里是int，按需修改
                maxval = int(max(values[col]))#这里是int，按需修改
                hash_num = min(constants.HASH_NUM, maxval-minval+1)
                self.col_info[col] = (minval, maxval)
                self.hash_num[col] = hash_num
        for col in constants.colset:
            vals = values[col]
            if vals is not None:
                for val in vals:
                    self.add_(col, val)


    def getvalues(self):
        if os.path.exists(constants.VALUE_CACHE):
            with open(constants.VALUE_CACHE,"rb") as f:
                return pickle.load(f)
        db = Database(constants.DATABASE_URL)
        collist = []
        for table, columns in constants.colset.items():
            for column in columns:
                collist.append((table, column))
        cols = ["{}.{}".format(i[0],i[1]) for i in collist]
        ValueList = Values(values=OrderedDict.fromkeys(cols, None))
        for table,col in collist:
            vals = db.sample(col,table,0.01)#采样率0.01
            valid = set([])
            for v in vals:
                if v[0] is not None:
                    valid.add(int(v[0]))
            ValueList.values[col] = valid
        with open(constants.VALUE_CACHE,"wb") as f:
            pickle.dump(ValueList.values,f)
        return ValueList.values

    
    def key_(self, col, value):
        (min, max) = self.col_info[col]
        key = math.ceil(self.hash_num[col]*(value-min+1)/(max-min+1)-1)
        return key

    def value_(self,col,key):
        key = key % self.hash_num[col]
        while key not in self.hash_bucket[col].keys():
            key = key+1
            key = key % self.hash_num[col]
        vals = self.hash_bucket[col][key]
        value = random.choice(vals)
        return value

    def add_(self, col, value):
        key = self.key_(col, value)
        if self.hash_bucket[col] == None:
            self.hash_bucket[col] = {}
        if key not in self.hash_bucket[col].keys():
            self.hash_bucket[col][key] = []
        self.hash_bucket[col][key].append(value)



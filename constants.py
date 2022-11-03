from pathlib import Path



# 数据路径
DATA_ROOT = Path("./data")
TEMP_ROOT = Path("./temp")

GRAMMAR_PATH = DATA_ROOT / "grammar" / "job.bnf"  # 语法文件，如果要更改语法，就修改这个文件
LARK_PATH = DATA_ROOT / "grammar" / "job.lark"  # 自动转化后的语法文件，这个一般不修改
BASE_GRAMMAR = DATA_ROOT / "bnf-lang" / "bnf.lark"  # 这个也不用修改
BASE = DATA_ROOT / "grammar"/"base.bnf"
# 这里是对数据库中的列进行采用，采样的值填充到查询中，如果要换数据集，或修改了语法，删除这个文件、
VALUE_CACHE = TEMP_ROOT / "value.pkl"


max_sequence_length = 300  # 最大的查询长度，一般达不到
HASH_NUM = 10  # 桶的数量


# 语义相关，一般不修改
op_mask_offset = {">": [0, 2],
                  "<": [1, 2],
                  "=": [0, 1, 2],
                  }
ops = [">", "<", "="]
need_range = ["predicate", "operator", "join_key", "value"]

# 处理过程中用到的一些正则表达式
reg_join = r"([A-Za-z_]*)\.([A-Za-z_]*)=([A-Za-z_]*)\.([A-Za-z_]*)"




# 要连接的数据库地址
DATABASE_URL = "postgres://postgres:1@192.168.31.102:21432/postgres"
# 语法修改的地方
# 查询中包含的表
tableset = ['PART', 'SUPPLIER', 'PARTSUPP', 'CUSTOMER', 'ORDERS', 'LINEITEM',
            'NATION', 'REGION']

# 查询中包含的列，只挑出了int 和 decimal
colset = {'PART': ['P_SIZE', 'P_RETAILPRICE'],
          'SUPPLIER': ['S_ACCTBAL'],
          'PARTSUPP': ['PS_AVAILQTY', 'PS_SUPPLYCOST'],
          'CUSTOMER': ['C_ACCTBAL'],
          'ORDERS': ['O_TOTALPRICE', 'O_SHIPPRIORITY'],
          'LINEITEM': ['L_LINENUMBER', 'L_QUANTITY', 'L_EXTENDEDPRICE', 'L_DISCOUNT', 'L_TAX'],
          'NATION': [],
          'REGION': []
          }
# 连接键(table1,table2):key
joinkey = {('PART', 'PARTSUPP'): ('P_PARTKEY', 'PS_PARTKEY'),
           ('SUPPLIER', 'PARTSUPP'): ('S_SUPPKEY', 'PS_SUPPKEY'),
           ('SUPPLIER', 'CUSTOMER'): ('S_NATIONKEY', 'C_NATIONKEY'),
           ('SUPPLIER', 'NATION'): ('S_NATIONKEY', 'N_NATIONKEY'),
           ('PARTSUPP', 'LINEITEM'): ('PS_PARTKEY', 'L_PARTKEY'),
           ('PARTSUPP', 'LINEITEM'): ('PS_SUPPKEY', 'L_SUPPKEY'),
           ('CUSTOMER', 'ORDERS'): ('C_CUSTKEY', 'O_CUSTKEY'),
           ('NATION', 'REGION'): ('N_REGIONKEY', 'R_REGIONKEY'),
           ('LINEITEM', 'ORDERS'): ('L_ORDERKEY', 'O_ORDERKEY')}




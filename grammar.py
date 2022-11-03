# 自动的语法文件生成工具
from io import BufferedWriter
import constants
from shutil import copyfile
import re
body = "::="


class Grammar:
    def __init__(self):
        pass

    def format(self):
        copyfile(constants.BASE, constants.GRAMMAR_PATH)
        with open(constants.GRAMMAR_PATH, "a") as f:
            self.join(f)
            self.predicate(f)
        self.bnftolark(constants.GRAMMAR_PATH, constants.LARK_PATH)
        
    # 生成连接语法
    def join(self, file: BufferedWriter):
        joinlist = []
        for tables, joinkeys in constants.joinkey.items():
            tableA, tableB = tables
            keyA, keyB = joinkeys
            joinlist.append(self.Terminal(
                "{}.{}={}.{}".format(tableA, keyA, tableB, keyB)))
        print(joinlist)
        file.write("{} {} ".format(self.Nonterminal("join"), body))
        file.write(" | ".join(joinlist))
        file.write("\n")

    # 生成谓词语法
    def predicate(self, file: BufferedWriter):
        predlist = []
        for table, columns in constants.colset.items():
            for column in columns:
                predlist.append(self.Terminal("{}.{}".format(table, column)))
        file.write("{} {} ".format(self.Nonterminal("column"), body))
        file.write(" | ".join(predlist))
        file.write("\n")

    def bnftolark(self, srcpath, destpath):
        with open(srcpath, 'r') as file:
            filedata = file.read()
            filedata = re.sub(r"<([A-Za-z_0-9]+)>", r'\1', filedata)
            filedata = filedata.replace("::=", ":")
            filedata = re.sub(
                r'(\s)([A-Za-z_]+)\s+:\s+""\s+\|\s+([A-Za-z_]+)', r'\1\2 : \3?', filedata)
            filedata = re.sub(
                r'#(.*)\n', "", filedata)
            with open(destpath, 'w') as file:
                file.write(filedata)

    def Nonterminal(self, symbol: str):
        return "<{}>".format(symbol)

    def Terminal(self, symbol: str):
        return "\"{}\"".format(symbol)

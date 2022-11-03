#语义错误检查
from collections import OrderedDict
from typing import Dict, NamedTuple, Optional
import torch
import constants
import parse_utils
import re

class ColMask(NamedTuple):
    op_mask: set
    val_mask: Dict[str, set]


class Info(NamedTuple):
    Column_info: Dict[str, Optional[ColMask]]

def col_info(colset):
    info = Info(Column_info=OrderedDict.fromkeys(colset,None))
    for col in colset:
        colmask = ColMask(op_mask = set([]),val_mask = {})
        for op in constants.ops:
            colmask.val_mask[op]=set([])
        info.Column_info[col] = colmask
    return info


class Semantic:
    def __init__(self, action_getter):
        self.rules_dict = action_getter.rules_dict
        self.symbol_names = action_getter.symbol_names
        self.action_offsets = action_getter.action_offsets
        self.non_terminal_ids = action_getter.non_terminal_ids
        self.action_list = self._action_list()
        self.action_num = len(self.action_list)
        first,last = self.get_range("column")
        self.info = col_info([i for i in range(first,last)])
        self.column = None
        self.operate = None
        self.longterm_mask = torch.ones(self.action_num, dtype=torch.bool)
        self.existing_join = []
        self.existing_table = set([])
        self.usecolumns = []
        self.firstPredicates = True
        
    def _action_list(self):
        actions = []
        for n_id in self.non_terminal_ids:
            for action in self.rules_dict[n_id]:
                n_name = self.symbol_names[n_id].name
                actions.append((n_name, n_id, list(action),[self.symbol_names[id].name for id in list(action)]))
        return actions

    def get_range(self, name):
        n_id = self.symbol_names.index(parse_utils.NonTerminal(name))
        first_action = self.action_offsets[n_id]
        last_action = first_action+len(self.rules_dict[n_id])
        return first_action, last_action

    def check(self, action,action_seq,symbol_stack):#根据动作更新状态
        n_name, n_id, rule,name = self.action_list[action]
        if n_name == "join":
            return self.action_join(action,symbol_stack,action_seq)
        elif n_name == "predicates":
            return self.action_predicates(action_seq)
        elif n_name == "column":
            return self.action_column(action)
        elif n_name == "operator":
            return self.action_operator(name[0])
        elif n_name == "value":
            return self.action_value(action,symbol_stack,action_seq)
        return self.longterm_mask

    def action_join(self,action,symbol_stack,action_seq):
        _, id, _, name = self.action_list[action]
        self.longterm_mask[action] = 0
        vm =re.search(constants.reg_join,name[0])
        tableA,tableB = vm.group(1),vm.group(3)
        self.existing_join.append(action)
        self.existing_table.add(tableA)
        self.existing_table.add(tableB)
        if len(self.existing_join)==len(self.rules_dict[id]):#已经没有连接条件可以选择了，整理action序列和语法分析栈
            if len(symbol_stack)>0 and symbol_stack[-4]==self.symbol_names.index(parse_utils.NonTerminal('joins')):
                symbol_stack.pop()
                symbol_stack.pop()
                symbol_stack.pop()
                symbol_stack.pop()
                action_seq[-1] += 1 #joins->join
        return self.longterm_mask
    
    def action_predicates(self,action_seq):#构造column_mask
        if self.firstPredicates:
            self.firstPredicates=False
            first_action,last_action = self.get_range('column') 
            self.longterm_mask[first_action:last_action] = 0
            offset = 0
            for table,columns in constants.colset.items():
                for _ in columns:
                    if table in self.existing_table:
                        self.longterm_mask[first_action+offset] = 1
                        self.usecolumns.append(first_action+offset)
                    offset+=1
            if len(self.usecolumns) == 0:#没有可用的列用来做谓词
                first_action,last_action = self.get_range('multi_table')
                action_seq[action_seq.index(first_action)] = last_action-1#只生成joins
                return None
        return self.longterm_mask


    def action_column(self, action):#构造opmask
        n_name, n_id, rule,name = self.action_list[action]
        self.column = action#当前列
        op_mask = torch.ones(self.action_num, dtype=torch.bool)#短期mask
        first_action,last_action = self.get_range('operator')
        count=0
        for op in self.info.Column_info[self.column].op_mask:
            op_mask[first_action+op] = 0
            count+=1
        if count==3:
            print("error")
        return torch.logical_and(op_mask,self.longterm_mask)
    
    def action_operator(self, name):
        # 更新op_mask
        self.op = name
        for offset in constants.op_mask_offset[name]:
            self.info.Column_info[self.column].op_mask.add(offset)
        if(len(self.info.Column_info[self.column].op_mask)==len(constants.ops)):
            if self.column in self.usecolumns:
                self.usecolumns.remove(self.column)#这一列没有可用的操作符，移除这一列
                self.longterm_mask[self.column] = 0
        # 计算val_mask
        val_mask=torch.ones(self.action_num, dtype=torch.bool)#短期mask
        (first,last) = self.get_range('value')
        if self.op in self.info.Column_info[self.column].val_mask.keys():#如果之前出现过
            for val in self.info.Column_info[self.column].val_mask[name]:
                val_mask[first+val] = 0
        return torch.logical_and(val_mask,self.longterm_mask)

    def action_value(self, action,symbol_stack,action_seq):
        # 更新val_mask
        (first_action,last_action) = self.get_range("value")
        offset = action-first_action
        if self.op == ">":
            for val in range(offset):
                self.info.Column_info[self.column].val_mask["<"].add(val)
                if len(self.info.Column_info[self.column].val_mask["<"])==constants.HASH_NUM:
                    if self.column in self.usecolumns:
                        self.usecolumns.remove(self.column)     
                        self.longterm_mask[self.column] = 0   
        elif self.op == "<" :
            for val in range(offset,constants.HASH_NUM):
                self.info.Column_info[self.column].val_mask[">"].add(val)
                if len(self.info.Column_info[self.column].val_mask[">"])==constants.HASH_NUM:
                    if self.column in self.usecolumns:
                        self.usecolumns.remove(self.column)
                        self.longterm_mask[self.column] = 0
        if len(self.usecolumns) == 0:#没有可用的列用来做谓词
            if len(symbol_stack)>0 and symbol_stack[-4] == self.symbol_names.index(parse_utils.NonTerminal('predicates')): 
                symbol_stack.pop()
                symbol_stack.pop()
                symbol_stack.pop()
                symbol_stack.pop()
                action_seq[-4]+=1
        return self.longterm_mask
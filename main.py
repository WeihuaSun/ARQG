import constants
import parse_utils
import torch
import torch.nn as nn
from torch.distributions import Categorical
from process import DataProcess
from grammar import Grammar
from semantic import Semantic


def reconstruct(sqls: list):
    dp = DataProcess()
    valid = []
    for sql in sqls:
        print(sql)
        q = dp.rebuild(sql)
        print(q)
        print("\n")
        if q is not None:
            valid.append(q)
    return valid


def parser():
    bnf_parser = parse_utils.CustomBNFParser(
        grammar_file_path=constants.BASE_GRAMMAR)
    _, rules_dict, symbol_names = bnf_parser.parse_file(
        constants.GRAMMAR_PATH, start="start")
    action_getter = parse_utils.SimpleTreeActionGetter(
        rules_dict, symbol_names)
    return action_getter

def generator(action_getter: parse_utils.SimpleTreeActionGetter, n: int):
    rules_dict = action_getter.rules_dict
    symbol_names = action_getter.symbol_names
    action_offsets = action_getter.action_offsets
    non_terminal_ids = action_getter.non_terminal_ids
    start_id = symbol_names.index(parse_utils.NonTerminal('start'))
    num_of_rules = sum(len(rules) for rules in rules_dict.values())

    action_masks = nn.Parameter(torch.empty(
        len(non_terminal_ids), num_of_rules, dtype=torch.bool), requires_grad=False)

    for non_terminal_id, rules in rules_dict.items():
        # Create the action mask for each non-terminal symbol
        action_mask = torch.zeros(num_of_rules, dtype=torch.bool)
        first_action = action_offsets[non_terminal_id]
        last_action = first_action + len(rules)
        action_mask[first_action:last_action] = 1
        action_masks[non_terminal_ids.index(
            non_terminal_id)].copy_(action_mask.data)
    # Semantic check
    sqls = []
    
    for _ in range(n):
        action_list = []
        symbol_stack = [start_id]
        check = Semantic(action_getter)#检测语法错误
        semantic_mask = torch.ones(num_of_rules,dtype=torch.bool)
        while True:
            if not symbol_stack or len(action_list) > constants.max_sequence_length:
                break
            symbol_id = symbol_stack.pop()
            prob = torch.log_softmax(torch.rand(num_of_rules), dim=-1)
            syntax_mask = action_masks[non_terminal_ids.index(symbol_id)]#语法检查
            unit_mask = torch.logical_and(syntax_mask,semantic_mask)
            try:
                action_dist = Categorical(logits=prob.masked_fill(
                unit_mask.bitwise_not().unsqueeze(0), float('-inf')))
            except:
                for i in action_list: 
                    print(check.action_list[i])
            finally:
                action = int(action_dist.sample())
                semantic_mask_ = check.check(action,action_list,symbol_stack)
                if semantic_mask_ is not None:
                    semantic_mask = semantic_mask_
                else:
                    continue
                action_list.append(action)
                for child_id in reversed(rules_dict[symbol_id][action - action_offsets[symbol_id]]):
                    if isinstance(symbol_names[child_id], parse_utils.NonTerminal):
                        symbol_stack.append(child_id)
        try:
            sql = action_getter.construct_text_partial(action_list)
        except:
            for i in action_list: 
                    print(check.action_list[i])
            return
        print(sql)
        sqls.append(sql)
    return sqls


if __name__ == "__main__":
    gen_num = 1000
    bnf = Grammar()
    bnf.format()
    action_getter = parser()
    sqls = generator(action_getter, gen_num)
    sqls = reconstruct(sqls)
    with open("random.sql", "w")as f:
        f.write("\n".join(sqls))

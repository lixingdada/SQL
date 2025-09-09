# syntaxAnalysis.py
# SQL语法分析器 - 基于LL(1)预测分析法

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from lexicalAnalysis import tokenize

class SyntaxAnalyzer:
    def __init__(self):
        # 说明：本分析器采用 LL(1) 预测分析。常见报错“X 在 a 处无产生式”
        # 多半是 FOLLOW 集未正确包含 a，或文法未覆盖该情形。下方的注释
        # 会标注 FIRST/FOLLOW 的传播位置，便于排查。
        # 定义SQL语法规则（LL(1)文法）
        # 格式：非终结符 -> 产生式右部
        # 参考C代码，使用更简单的文法避免冲突
        self.grammar = {
            'Prog': [['Query', ';']],
            'Query': [
                ['SELECT', 'SelList', 'FROM', 'Tbl', 'WhereOpt'],
                ['INSERT', 'INTO', 'Tbl', 'VALUES', '(', 'ValList', ')'],
                ['UPDATE', 'Tbl', 'SET', 'SetList'],
                ['DELETE', 'FROM', 'Tbl']
            ],
            'SelList': [
                ['*'],
                ['ID', 'SelListRest']
            ],
            'SelListRest': [
                [],  # ε
                [',', 'ID', 'SelListRest']
            ],
            'Tbl': [['ID']],
            # WHERE 子句（可选）
            'WhereOpt': [
                [],  # ε
                ['WHERE', 'Cond']
            ],
            # 条件表达式：支持 AND / OR 连接
            'Cond': [
                ['Expr', 'RelOp', 'Expr', 'CondTail']
            ],
            'CondTail': [
                [],  # ε
                ['AND', 'Cond'],
                ['OR', 'Cond']
            ],
            'Expr': [
                ['ID'],
                ['NUM'],
                ['STRING']
            ],
            'RelOp': [
                ['='], ['<>'], ['<'], ['>'], ['<='], ['>='], ['!=']
            ],
            'ValList': [
                ['Val', 'ValListRest']
            ],
            'ValListRest': [
                [],  # ε
                [',', 'Val', 'ValListRest']
            ],
            'Val': [
                ['ID'],
                ['NUM'],
                ['STRING']
            ],
            'SetList': [
                ['ID', '=', 'Val', 'SetListRest']
            ],
            'SetListRest': [
                [],  # ε
                [',', 'ID', '=', 'Val', 'SetListRest']
            ]
        }
        
        # 终结符集合
        self.terminals = {
            'SELECT', 'FROM', 'WHERE', 'INSERT', 'INTO', 'VALUES', 'UPDATE', 'SET', 'DELETE',
            'AND', 'OR',
            'ID', 'NUM', 'STRING', '*', ',', ';', '(', ')', 'EOF',
            # 关系运算符
            '=', '<>', '<', '>', '<=', '>=', '!='
        }
        
        # 词法分析器token类型到语法分析器终结符的映射
        # 词法 token → 语法终结符 的映射：
        # - KEYWORD: 大写化后直接作为终结符（SELECT/WHERE/...）
        # - ID/NUM/STRING: 归一为同名终结符
        # - RANGE/OP: 使用其字面量作为终结符（如 ',' ';' '(' ')' 以及 '<=' '<>' 等）
        # - COMMENT/UNKNOWN: 语法阶段忽略
        self.token_to_terminal = {
            'KEYWORD': lambda value: value.upper(),
            'ID': lambda value: 'ID',
            'NUM': lambda value: 'NUM',
            'STRING': lambda value: 'STRING',
            'RANGE': lambda value: value,
            'OP': lambda value: value,
            'COMMENT': lambda value: None,
            'EOF': lambda value: 'EOF'
        }
        
        # 非终结符集合
        self.non_terminals = set(self.grammar.keys())
        
        # 预测分析表
        self.parsing_table = {}
        
        # 初始化
        self._compute_first_sets()
        self._compute_follow_sets()
        self._build_parsing_table()

    # ========================= AST 结构体 =========================
    class ASTNode:
        pass

    class Program(ASTNode):
        def __init__(self, query):
            self.query = query
        def __repr__(self):
            return f"Program({self.query!r})"

    class Select(ASTNode):
        def __init__(self, columns, table, where):
            self.columns = columns
            self.table = table
            self.where = where
        def __repr__(self):
            return f"Select(columns={self.columns!r}, table={self.table!r}, where={self.where!r})"

    class Columns(ASTNode):
        def __init__(self, all_columns=False, names=None):
            self.all = all_columns
            self.names = names or []
        def __repr__(self):
            return f"Columns(all={self.all}, names={self.names})"

    class Table(ASTNode):
        def __init__(self, name):
            self.name = name
        def __repr__(self):
            return f"Table({self.name!r})"

    class Identifier(ASTNode):
        def __init__(self, name):
            self.name = name
        def __repr__(self):
            return f"Id({self.name!r})"

    class Number(ASTNode):
        def __init__(self, value):
            self.value = value
        def __repr__(self):
            return f"Num({self.value})"

    class String(ASTNode):
        def __init__(self, value):
            self.value = value
        def __repr__(self):
            return f"Str({self.value})"

    class BinaryOp(ASTNode):
        def __init__(self, left, op, right):
            self.left = left
            self.op = op
            self.right = right
        def __repr__(self):
            return f"BinaryOp({self.left!r} {self.op!r} {self.right!r})"
    
    def _compute_first_sets(self):
        """计算 FIRST 集：某非终结符能以哪些终结符开头。
        迭代直至收敛。若产生式可推导 ε，则将 ε 纳入 FIRST。
        """
        self.first_sets = {}
        
        # 初始化所有非终结符的FIRST集合
        for nt in self.non_terminals:
            self.first_sets[nt] = set()
        
        # 迭代直到收敛
        changed = True
        while changed:
            changed = False
            for nt, productions in self.grammar.items():
                for production in productions:
                    old_size = len(self.first_sets[nt])
                    self._add_first_of_production(nt, production)
                    if len(self.first_sets[nt]) > old_size:
                        changed = True
    
    def _add_first_of_production(self, nt, production):
        """将产生式 nt→production 的贡献加入 FIRST(nt)。
        规则：遇到第一个不可空符号即停止；若前缀均可空，传播 ε。
        """
        if not production:  # 空产生式
            self.first_sets[nt].add('ε')
            return
        
        # 检查产生式中的每个符号
        for i, symbol in enumerate(production):
            if symbol in self.terminals:
                # 终结符，直接添加
                self.first_sets[nt].add(symbol)
                break
            elif symbol in self.non_terminals:
                # 非终结符，添加其FIRST集合（除了ε）
                first_of_symbol = self.first_sets[symbol] - {'ε'}
                self.first_sets[nt].update(first_of_symbol)
                
                # 如果该非终结符的FIRST集合不包含ε，则停止
                if 'ε' not in self.first_sets[symbol]:
                    break
                
                # 如果是最后一个符号且包含ε，则添加ε
                if i == len(production) - 1:
                    self.first_sets[nt].add('ε')
    
    def _compute_follow_sets(self):
        """计算 FOLLOW 集：某非终结符后可以跟随哪些终结符。
        关键传播点：
        - 若 A→αBβ，FOLLOW(B) ⊇ FIRST(β)-{ε}
        - 若 A→αBβ 且 β ⇒* ε，FOLLOW(B) ⊇ FOLLOW(A)
        - 开始符号 FOLLOW 含 $。
        """
        self.follow_sets = {}

        # 初始化所有非终结符的FOLLOW集合
        for nt in self.non_terminals:
            self.follow_sets[nt] = set()

        # 开始符号的FOLLOW集合包含$
        self.follow_sets['Prog'].add('$')

        # 迭代直到收敛
        changed = True
        while changed:
            changed = False
            for nt, productions in self.grammar.items():
                for production in productions:
                    if self._add_follow_of_production(nt, production):
                        changed = True
    
    def _add_follow_of_production(self, nt, production):
        """应用一条产生式的 FOLLOW 传播规则。返回是否发生变化。
        常见调试：若在 a 处“无产生式”，检查包含该位点的非终结符
        是否通过此处将 a 传播进了它的 FOLLOW。
        """
        any_changed = False
        for i, symbol in enumerate(production):
            if symbol in self.non_terminals:
                before = set(self.follow_sets[symbol])
                # 计算该非终结符后面的符号的FIRST集合
                remaining = production[i+1:]
                if not remaining:
                    # 如果后面没有符号，添加产生式左部的FOLLOW集合
                    self.follow_sets[symbol].update(self.follow_sets[nt])
                else:
                    # 计算剩余符号的FIRST集合
                    first_of_remaining = self._first_of_sequence(remaining)
                    if 'ε' in first_of_remaining:
                        # 如果剩余符号可以推导出ε，添加产生式左部的FOLLOW集合
                        self.follow_sets[symbol].update(self.follow_sets[nt])
                        first_of_remaining = set(first_of_remaining)
                        first_of_remaining.discard('ε')
                    self.follow_sets[symbol].update(first_of_remaining)

                if before != self.follow_sets[symbol]:
                    any_changed = True
        return any_changed
    
    def _first_of_sequence(self, sequence):
        """计算符号序列的FIRST集合"""
        if not sequence:
            return {'ε'}
        
        first_set = set()
        for i, symbol in enumerate(sequence):
            if symbol in self.terminals:
                first_set.add(symbol)
                break
            elif symbol in self.non_terminals:
                first_of_symbol = self.first_sets[symbol] - {'ε'}
                first_set.update(first_of_symbol)
                if 'ε' not in self.first_sets[symbol]:
                    break
                if i == len(sequence) - 1:
                    first_set.add('ε')
        
        return first_set
    
    def _build_parsing_table(self):
        """构建预测分析表 M[非终结符][终结符] → 产生式。
        填表规则：
        - 对于 A→α，∀ a∈FIRST(α)-{ε}，置 M[A][a]=α
        - 若 ε∈FIRST(α)，∀ b∈FOLLOW(A)，置 M[A][b]=ε
        出现“冲突”打印警告，说明文法非 LL(1) 或 FIRST/FOLLOW 传播缺失。
        """
        # 初始化分析表
        for nt in self.non_terminals:
            self.parsing_table[nt] = {}
            for terminal in self.terminals:
                self.parsing_table[nt][terminal] = None
        
        # 填充分析表
        for nt, productions in self.grammar.items():
            for production in productions:
                first_of_production = self._first_of_sequence(production)
                
                # 对于FIRST集合中的每个终结符
                for terminal in first_of_production - {'ε'}:
                    if self.parsing_table[nt][terminal] is not None:
                        print(f"警告：分析表冲突 {nt}[{terminal}]")
                    self.parsing_table[nt][terminal] = production
                
                # 如果产生式可以推导出ε
                if 'ε' in first_of_production:
                    for terminal in self.follow_sets[nt]:
                        if self.parsing_table[nt][terminal] is not None:
                            print(f"警告：分析表冲突 {nt}[{terminal}]")
                        self.parsing_table[nt][terminal] = []
    
    def analyze(self, sql_text, debug=False):
        """对SQL文本进行语法分析。
        debug=True 时，会输出映射、栈变化、表查找等详细信息。
        """
        # 词法分析
        tokens = tokenize(sql_text)
        # 复用基于 tokens 的接口
        return self.analyze_tokens(tokens, debug=debug)

    # ========================= 基于 tokens 构建 AST（递归下降） =========================
    def build_ast(self, sql_text):
        tokens = tokenize(sql_text)
        return self.build_ast_from_tokens(tokens)

    def _map_tokens(self, tokens):
        mapped = []
        for ttype, tval, ln, col in tokens:
            fn = self.token_to_terminal.get(ttype)
            term = fn(tval) if fn else None
            if term is None:
                continue
            mapped.append((term, tval, ln, col))
        mapped.append(('EOF', '$', 0, 0))
        return mapped

    def build_ast_from_tokens(self, tokens):
        stream = self._map_tokens(tokens)
        self._idx = 0
        self._stream = stream
        prog = self._parse_Prog()
        self._expect('EOF')
        return prog

    def _current(self):
        return self._stream[self._idx]

    def _accept(self, term):
        tok = self._current()
        if tok[0] == term:
            self._idx += 1
            return tok
        return None

    def _expect(self, term):
        tok = self._current()
        if tok[0] != term:
            raise SyntaxError(f"期望 {term}，得到 {tok[0]}")
        self._idx += 1
        return tok

    # Prog -> Query ;
    def _parse_Prog(self):
        q = self._parse_Query()
        self._expect(';')
        return SyntaxAnalyzer.Program(q)

    # Query -> SELECT SelList FROM Tbl WhereOpt | ...（目前仅实现 SELECT 路径以生成 AST）
    def _parse_Query(self):
        if self._accept('SELECT'):
            cols = self._parse_SelList()
            self._expect('FROM')
            tbl = self._parse_Tbl()
            where = self._parse_WhereOpt()
            return SyntaxAnalyzer.Select(cols, tbl, where)
        # 其它语句可按需扩展成 AST
        raise NotImplementedError('当前 AST 构建仅实现 SELECT 语句')

    # SelList -> * | ID SelListRest
    def _parse_SelList(self):
        if self._accept('*'):
            return SyntaxAnalyzer.Columns(all_columns=True)
        id_tok = self._expect('ID')
        ids = [id_tok[1]]
        ids.extend(self._parse_SelListRest())
        return SyntaxAnalyzer.Columns(all_columns=False, names=ids)

    # SelListRest -> ε | , ID SelListRest
    def _parse_SelListRest(self):
        names = []
        if self._accept(','):
            id_tok = self._expect('ID')
            names.append(id_tok[1])
            names.extend(self._parse_SelListRest())
        return names

    # Tbl -> ID
    def _parse_Tbl(self):
        id_tok = self._expect('ID')
        return SyntaxAnalyzer.Table(id_tok[1])

    # WhereOpt -> ε | WHERE Cond
    def _parse_WhereOpt(self):
        if self._accept('WHERE'):
            return self._parse_Cond()
        return None

    # Cond -> Expr RelOp Expr CondTail
    def _parse_Cond(self):
        left = self._parse_Expr()
        op = self._parse_RelOp()
        right = self._parse_Expr()
        node = SyntaxAnalyzer.BinaryOp(left, op, right)
        tail = self._parse_CondTail()
        if tail is not None:
            op2, rhs = tail
            node = SyntaxAnalyzer.BinaryOp(node, op2, rhs)
        return node

    # CondTail -> ε | AND Cond | OR Cond
    def _parse_CondTail(self):
        if self._accept('AND'):
            rhs = self._parse_Cond()
            return ('AND', rhs)
        if self._accept('OR'):
            rhs = self._parse_Cond()
            return ('OR', rhs)
        return None

    # Expr -> ID | NUM | STRING
    def _parse_Expr(self):
        tok = self._current()
        if tok[0] == 'ID':
            self._idx += 1
            return SyntaxAnalyzer.Identifier(tok[1])
        if tok[0] == 'NUM':
            self._idx += 1
            return SyntaxAnalyzer.Number(tok[1])
        if tok[0] == 'STRING':
            self._idx += 1
            return SyntaxAnalyzer.String(tok[1])
        raise SyntaxError(f"Expr 起始符错误：{tok[0]}")

    # RelOp -> 关系运算符字面量
    def _parse_RelOp(self):
        for op in ['=', '<>', '<', '>', '<=', '>=', '!=']:
            if self._accept(op):
                return op
        tok = self._current()
        raise SyntaxError(f"关系运算符错误：{tok[0]}")
    def analyze_tokens(self, tokens, debug=False):
        """基于词法 tokens 进行语法分析。
        输入：[(type, value, line, col), ...]
        输出：四元式列表 [步骤, [语法栈], (输入串), 表达式]
        调试建议：可先调用 debug_dump() 查看 FIRST/FOLLOW/表项。
        """
        if not tokens:
            return self._create_error_output("输入为空")

        # 转换token类型为终结符
        converted_tokens = []
        for token_type, token_value, line, col in tokens:
            # 将词法 token 映射为语法终结符；如为注释/未知则忽略
            if token_type in self.token_to_terminal:
                terminal = self.token_to_terminal[token_type](token_value)
                if terminal is None:
                    if debug:
                        print(f"[Map] skip token: type={token_type}, value={token_value}")
                    continue
                converted_tokens.append((terminal, token_value, line, col))
                if debug:
                    print(f"[Map] ({token_type}, {token_value}) -> terminal='{terminal}' @({line},{col})")
            else:
                if debug:
                    print(f"[Map] unknown token type '{token_type}', skip")
                continue

        # 添加EOF标记
        converted_tokens.append(('EOF', '$', 0, 0))
        if debug:
            preview = [(t[0], t[1]) for t in converted_tokens]
            print(f"[Input] converted stream: {preview}")

        # 初始化分析栈
        stack = ['$', 'Prog']  # 栈底是$，栈顶是开始符号
        input_tokens = converted_tokens.copy()
        step = 0
        output = []
        
        while stack:
            step += 1
            top = stack[-1]
            current_token = input_tokens[0] if input_tokens else ('EOF', '$', 0, 0)
            current_type = current_token[0]
            
            # 构建当前步骤的四元式（仅展示前若干输入，便于阅读）
            stack_str = str(stack)
            input_str = str([(t[0], t[1]) for t in input_tokens[:3]])  # 只显示前3个token
            expression = ""
            
            if top == '$' and current_type == 'EOF':
                # 接受
                expression = "接受"
                output.append([step, stack_str, input_str, expression])
                break
            elif top in self.terminals:
                if top == current_type:
                    # 匹配
                    expression = f"匹配 {current_type}"
                    if debug:
                        print(f"[Step {step}] match terminal '{current_type}'")
                    stack.pop()
                    input_tokens.pop(0)
                else:
                    # 错误
                    expression = f"错误：期望 {top}，得到 {current_type}"
                    if debug:
                        print(f"[Step {step}] ERROR expect '{top}' but got '{current_type}'")
                    output.append([step, stack_str, input_str, expression])
                    return self._create_error_output(expression)
            elif top in self.non_terminals:
                # 查预测分析表：若无表项，多半是 FOLLOW 未包含当前终结符
                production = self.parsing_table[top].get(current_type)
                if production is None:
                    # 错误
                    expression = f"错误：{top} 在 {current_type} 处无产生式"
                    if debug:
                        print(f"[Step {step}] TABLE MISS: M[{top}][{current_type}] is None")
                        print(f"  FIRST({top}) = {sorted(self.first_sets[top])}")
                        print(f"  FOLLOW({top}) = {sorted(self.follow_sets[top])}")
                        # 打印该非终结符的非空表项，帮助定位
                        row = {t: self.parsing_table[top][t] for t in self.terminals if self.parsing_table[top][t] is not None}
                        for t, prod in row.items():
                            rhs = 'ε' if not prod else ' '.join(prod)
                            print(f"  M[{top}][{t}] = {rhs}")
                    output.append([step, stack_str, input_str, expression])
                    return self._create_error_output(expression)
                else:
                    # 应用产生式
                    stack.pop()
                    if production:  # 非空产生式
                        for symbol in reversed(production):
                            stack.append(symbol)
                        expression = f"用 {top} -> {' '.join(production)}"
                        if debug:
                            print(f"[Step {step}] reduce: {top} -> {' '.join(production)}")
                    else:  # 空产生式
                        expression = f"用 {top} -> ε"
                        if debug:
                            print(f"[Step {step}] reduce: {top} -> ε")
            else:
                # 错误
                expression = f"错误：未知符号 {top}"
                if debug:
                    print(f"[Step {step}] ERROR unknown symbol on stack: {top}")
                output.append([step, stack_str, input_str, expression])
                return self._create_error_output(expression)
            
            output.append([step, stack_str, input_str, expression])
        
        return output

    
    def _create_error_output(self, error_msg):
        """创建错误输出"""
        return [[1, "[]", "[]", error_msg]]
    
    def print_analysis_result(self, result):
        """打印分析结果 - 四元式格式：[步骤, [语法栈], (输入串), 表达式]"""
        print("语法分析结果：")
        print("=" * 80)
        for step_info in result:
            step, stack, input_str, expression = step_info
            # 严格按照四元式格式输出
            print(f"[{step}, {stack}, {input_str}, {expression}]")
        print("=" * 80)

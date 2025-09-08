# syntaxAnalysis.py
# 辅助脚本：调用 word.tokenize 并按四元组或语句分组返回结果
# 提供函数：quads(text) -> list of dicts; split_statements(tokens) -> list of token-lists

from lexicalAnalysis import tokenize

def quads(text):
    """返回词法分析的四元组列表，每项为字典：{'type','value','line','column'}"""
    raw = tokenize(text)
    return [
        {'type': t[0], 'value': t[1], 'line': t[2], 'column': t[3]} for t in raw
    ]

def split_statements(tokens):
    """根据分号 ';' 将 token 列表分割成若干语句的 token 列表（包括分号作为语句结束符）。
    参数 tokens 为 quads(text) 返回的字典列表或 word.tokenize 的原始元组列表。
    返回值为列表，每个元素为该语句的 token 列表（同样为字典格式）。
    """
    # 允许传入元组或字典，统一成字典形式
    unified = []
    for t in tokens:
        if isinstance(t, tuple) or isinstance(t, list):
            unified.append({'type': t[0], 'value': t[1], 'line': t[2], 'column': t[3]})
        else:
            unified.append(t)

    stmts = []
    cur = []
    for tok in unified:
        cur.append(tok)
        if tok['type'] == 'RANGE' and tok['value'] == ';':
            stmts.append(cur)
            cur = []
    if cur:
        stmts.append(cur)
    return stmts

if __name__ == '__main__':
    # 简单命令行测试：从 stdin 读取 SQL，输出四元组和按语句分组结果
    import sys
    data = sys.stdin.read()
    if not data:
        print('请通过管道或重定向提供 SQL 输入，例如: python syntaxAnalysis.py < test.sql')
        sys.exit(0)

    q = quads(data)
    for item in q:
        val = (item['value'] or '').replace("'", "\\'")
        print(f"Output(type='{item['type']}', value='{val}', line={item['line']}, column={item['column']})")

    print('\n-- Statements split --')
    stmts = split_statements(q)
    for i, s in enumerate(stmts, 1):
        print(f'-- Statement {i} ({len(s)} tokens) --')
        for tok in s:
            v = (tok['value'] or '').replace("'", "\\'")


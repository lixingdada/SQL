import sys
import os

# 允许从当前目录导入本包模块
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from lexicalAnalysis import tokenize
from syntaxAnalysis import SyntaxAnalyzer


def main():
    # 你可以在这里替换要测试的 SQL 语句
    sql = "-- this is comment\nSELECT * FROM t WHERE x <= 10 AND y <> 0;"

    print("SQL:", sql)

    # 1) 词法分析 → tokens（原生四元组）
    tokens = tokenize(sql)

    print("\n词法分析输出 (type, value, line, col)：")
    for i, (typ, val, ln, col) in enumerate(tokens, 1):
        print(i, (typ, val, ln, col))

    # 为便于直观看到语法阶段的输入，展示从 token 到语法终结符的映射预览
    analyzer = SyntaxAnalyzer()
    mapped = []
    for (typ, val, ln, col) in tokens:
        fn = analyzer.token_to_terminal.get(typ)
        t = fn(val) if fn else None
        if t is None:
            continue
        mapped.append(t)
    mapped.append('EOF')
    print("\n传给语法分析器的终结符序列：")
    print(mapped)

    # 2) 语法分析（基于 tokens）→ AST
    try:
        ast = analyzer.build_ast_from_tokens(tokens)
        print("\n语法分析 AST：")
        print(ast)
    except Exception as e:
        print("\n语法分析失败：", e)


if __name__ == "__main__":
    main()



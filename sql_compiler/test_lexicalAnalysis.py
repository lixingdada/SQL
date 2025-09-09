# test_lexicalAnalysis.py
# 测试用例：调用 word.tokenize 并打印四元组输出
from lexicalAnalysis import tokenize

cases = [
    ("Test1: 多行注释 + 简单 SELECT",
     """/* test_sql_program */
SELECT name, age
FROM Students
WHERE age > 20;"""),

    ("Test2: 字符串单引号转义",
     "INSERT INTO authors VALUES ('O''Reilly', 1978);"),

    ("Test3: 单行注释与复合运算符",
     "-- this is comment\nSELECT * FROM t WHERE x <= 10 AND y <> 0;"),

    ("Test4: 数据类型关键字识别",
     "CREATE TABLE t (id INT, name CHAR(10));"),

    ("Test5: 浮点数识别",
     "SELECT price FROM items WHERE price > 3.1415;")
]

if __name__ == '__main__':
    for title, sql in cases:
        print('\n' + title)
        tokens = tokenize(sql)
        for t in tokens:
            typ, val, ln, col = t
            # 转义内部单引号以便显示
            display = (val or '').replace("'", "\\'")
            print(f"Output(type='{typ}', value='{display}', line={ln}, column={col})")


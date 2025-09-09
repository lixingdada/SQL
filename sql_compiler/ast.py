# -*- coding: utf-8 -*-
"""
此文件定义了抽象语法树 (AST) 的所有节点类。
语法分析器 (Parser) 的输出就是一个由这些类的实例构成的树状结构。
每个类代表了 SQL 语言中的一个语法构造。
"""
from dataclasses import dataclass
from typing import List, Optional, Union

from .token import Token


# --- 基础节点 ---

class ASTNode:
    """所有 AST 节点的基类，用于类型检查和未来的扩展。"""
    pass


# --- 表达式节点 (Expressions) ---
# 表达式是会产生一个值的代码片段，例如字面量、列名、二元运算等。

@dataclass
class Literal(ASTNode):
    """字面量节点，如数字 '123' 或字符串 'hello'。"""
    token: Token  # The token representing the literal (e.g., NUMBER, STRING)
    value: Union[int, float, str]

@dataclass
class Identifier(ASTNode):
    """标识符节点，如表名或列名。"""
    token: Token  # The IDENTIFIER token
    value: str

@dataclass
class BinaryExpr(ASTNode):
    """二元表达式节点，如 'age > 20'。"""
    left: 'Expression'        # 左操作数
    operator: Token           # 操作符 (e.g., =, >, <)
    right: 'Expression'       # 右操作数

# Expression 类型可以是任何表达式节点的联合
Expression = Union[Literal, Identifier, BinaryExpr]


# --- 语句节点 (Statements) ---
# 语句是执行一个动作的完整指令。

@dataclass
class ColumnDefinition(ASTNode):
    """列定义节点，用于 CREATE TABLE 语句。"""
    column_name: Identifier
    data_type: Token  # The data type token (e.g., INT, VARCHAR)

@dataclass
class CreateTableStatement(ASTNode):
    """CREATE TABLE 语句节点。"""
    table_name: Identifier
    columns: List[ColumnDefinition]

@dataclass
class InsertStatement(ASTNode):
    """INSERT INTO 语句节点。"""
    table_name: Identifier
    values: List[Literal]  # 简化版：只支持字面量列表

@dataclass
class SelectStatement(ASTNode):
    """SELECT 语句节点。"""
    select_list: List[Union[Identifier, Token]]  # 列名列表或 '*' (ASTERISK Token)
    from_table: Identifier
    where_clause: Optional[BinaryExpr] = None

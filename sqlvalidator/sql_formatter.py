from sqlvalidator.grammar.lexer import SQLStatementParser
from sqlvalidator.grammar.tokeniser import to_tokens


def format_sql(sql_string: str) -> str:
    return SQLStatementParser.parse(to_tokens(sql_string)).transform()

from typing import List

from sqlvalidator.grammar.lexer import ParsingError, SQLStatementParser
from sqlvalidator.grammar.tokeniser import to_tokens


class SQLQuery:
    def __init__(self, sql: str):
        self.sql = sql
        self.validated = False
        self.errors: List[str] = []

    def is_valid(self) -> bool:
        if not self.validated:
            self._validate()
        return len(self.errors) == 0

    def _validate(self):
        self.validated = True
        try:
            select_statement = SQLStatementParser.parse(to_tokens(self.sql))
            self.errors = select_statement.validate()
        except ParsingError as ex:
            self.errors.append(str(ex))


def parse(sql: str) -> SQLQuery:
    query = SQLQuery(sql)
    return query

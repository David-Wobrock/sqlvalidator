from typing import List

from sqlvalidator.grammar.lexer import ParsingError, SQLStatementParser
from sqlvalidator.grammar.tokeniser import to_tokens


class SQLQuery:
    def __init__(self, sql: str):
        self.sql = sql
        self._sql_query = None
        self.validated = False
        self.errors: List[str] = []

    @property
    def sql_query(self):
        if self._sql_query is None:
            self._sql_query = SQLStatementParser.parse(to_tokens(self.sql))
        return self._sql_query

    def format(self) -> str:
        return self.sql_query.transform()

    def is_valid(self) -> bool:
        if not self.validated:
            self._validate()
        return len(self.errors) == 0

    def _validate(self):
        self.validated = True
        try:
            self.errors = self.sql_query.validate()
        except ParsingError as ex:
            self.errors.append(str(ex))


def parse(sql: str) -> SQLQuery:
    query = SQLQuery(sql)
    return query

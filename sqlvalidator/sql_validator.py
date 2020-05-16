from sqlvalidator.grammar.lexer import SQLStatementParser, to_tokens, ParsingError


class SQLQuery:
    def __init__(self, sql: str):
        self.sql = sql
        self.validated = False
        self.errors = []

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

class SQLQuery:
    def __init__(self, sql: str):
        self.sql = sql
        self.validated = False
        self.errors: list = []

    def is_valid(self) -> bool:
        if not self.validated:
            self._validate()
        return len(self.errors) == 0

    def _validate(self):
        self.validated = True
        # TODO: to be implemented


def parse(sql: str) -> SQLQuery:
    query = SQLQuery(sql)
    return query

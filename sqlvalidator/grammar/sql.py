from typing import Any


def transform(obj: Any) -> str:
    if hasattr(obj, "transform"):
        return obj.transform()
    return str(obj)


class SelectStatement:
    def __init__(self, expressions, from_statement):
        self.expressions = expressions
        self.from_statement = from_statement

    def transform(self, is_subquery=False):
        if len(self.expressions) == 1:
            statement_str = "SELECT {}".format(self.expressions[0])
        else:
            statement_str = "SELECT\n {}".format(
                ",\n ".join(map(str, self.expressions))
            )

        if self.from_statement:
            if isinstance(self.from_statement, Parenthesis):
                from_str = "(\n{}\n)".format(
                    self.from_statement.args[0].transform(is_subquery=True)
                )
            else:
                from_str = str(self.from_statement)
            statement_str += "\nFROM {}".format(from_str)
        if is_subquery:
            statement_str = " " + statement_str.replace("\n", "\n ")
        else:
            statement_str += ";"
        return statement_str

    def __eq__(self, other):
        return (
            self.from_statement == other.from_statement
            and len(self.expressions) == len(other.expressions)
            and all(a == o for a, o in zip(self.expressions, other.expressions))
        )


class Expression:
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return str(self.value)

    def __eq__(self, other):
        return self.value == other.value


class FunctionCall(Expression):
    def __init__(self, function_name, *args):
        self.function_name = function_name
        self.args = args

    def __str__(self):
        return "{}({})".format(
            self.function_name.upper(), ", ".join(map(str, self.args))
        )

    def __repr__(self):
        return "<FunctionCall {} - {}>".format(
            self.function_name, ", ".join(map(repr, self.args))
        )

    def __eq__(self, other):
        return (
            self.function_name == other.function_name
            and len(self.args) == len(other.args)
            and all(a == o for a, o in zip(self.args, other.args))
        )


class Column(Expression):
    pass


class String(Expression):
    def __init__(self, value, quotes):
        super().__init__(value)
        self.quotes = quotes

    def __str__(self):
        return "{quotes}{value}{quotes}".format(quotes=self.quotes, value=self.value)


class Integer(Expression):
    def __init__(self, value):
        super().__init__(int(value))

    def __str__(self):
        return str(self.value)


class Parenthesis(Expression):
    def __init__(self, *args):
        self.args = args

    def __str__(self):
        return "({})".format(", ".join(map(str, self.args)))

    def __eq__(self, other):
        return len(self.args) == len(other.args) and all(
            a == o for a, o in zip(self.args, other.args)
        )


class Alias(Expression):
    def __init__(self, expression, alias, with_as):
        self.expression = expression
        self.alias = alias
        self.with_as = with_as

    def __str__(self):
        return "{}{}{}".format(
            self.expression, " AS " if self.with_as else " ", self.alias,
        )

    def __eq__(self, other):
        return self.expression == other.expression and self.alias == other.alias


class ArithmaticOperator(Expression):
    def __init__(self, operator, *args):
        self.operator = operator
        self.args = args

    def __str__(self):
        join_str = " {} ".format(self.operator)
        return join_str.join(map(str, self.args))

    def __eq__(self, other):
        return (
            self.operator == other.operator
            and len(self.args) == len(other.args)
            and all(a == o for a, o in zip(self.args, other.args))
        )


class Addition(ArithmaticOperator):
    def __init__(self, *args):
        super().__init__("+", args)


class Table(Expression):
    pass

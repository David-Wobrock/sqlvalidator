from typing import Any


def transform(obj: Any) -> str:
    if hasattr(obj, "transform"):
        return obj.transform()
    return str(obj)


class SelectStatement:
    def __init__(
        self,
        expressions,
        select_all=False,
        select_distinct=False,
        select_distinct_on=None,
        from_statement=None,
        where_clause=None,
        semi_colon=True,
    ):
        self.expressions = expressions
        self.select_all = select_all
        self.select_distinct = select_distinct
        self.select_distinct_on = select_distinct_on
        self.from_statement = from_statement
        self.where_clause = where_clause
        self.semi_colon = semi_colon

    def transform(self, is_subquery=False):
        statement_str = "SELECT"
        if self.select_all:
            statement_str += " ALL"
        elif self.select_distinct:
            statement_str += " DISTINCT"
            if self.select_distinct_on:
                statement_str += " ON ({})".format(
                    ", ".join(map(str, self.select_distinct_on))
                )

        if len(self.expressions) == 1:
            statement_str += " {}".format(self.expressions[0])
        else:
            statement_str += "\n {}".format(",\n ".join(map(str, self.expressions)))

        if self.from_statement:
            if isinstance(self.from_statement, Parenthesis):
                from_str = "(\n{}\n)".format(
                    self.from_statement.args[0].transform(is_subquery=True)
                )
            else:
                from_str = str(self.from_statement)
            statement_str += "\nFROM {}".format(from_str)

        if self.where_clause:
            statement_str += "\nWHERE {}".format(transform(self.where_clause))

        if is_subquery:
            statement_str = " " + statement_str.replace("\n", "\n ")
        elif self.semi_colon:
            statement_str += ";"
        return statement_str

    def validate(self):
        errors = []
        if isinstance(self.from_statement, Parenthesis) and isinstance(
            self.from_statement.args[0], SelectStatement
        ):
            known_fields = self.from_statement.args[0].known_fields
        elif isinstance(self.from_statement, Table):
            known_fields = {"*"}
        else:
            known_fields = set()

        if "*" in known_fields:
            return []

        for e in self.expressions:
            errors += e.validate(known_fields)
        if self.where_clause:
            errors += self.where_clause.validate(known_fields)
        return errors

    @property
    def known_fields(self):
        fields = []
        for e in self.expressions:
            if isinstance(e, Column):
                fields.append(e.value)
            elif isinstance(e, Alias):
                fields.append(e.alias)
        return fields

    def __eq__(self, other):
        return (
            type(self) == type(other)
            and self.select_all == other.select_all
            and self.select_distinct == other.select_distinct
            and (
                (self.select_distinct_on is None and other.select_distinct_on is None)
                or (
                    len(self.select_distinct_on) == len(other.select_distinct_on)
                    and all(
                        a == o
                        for a, o in zip(
                            self.select_distinct_on, other.select_distinct_on
                        )
                    )
                )
            )
            and self.from_statement == other.from_statement
            and len(self.expressions) == len(other.expressions)
            and all(a == o for a, o in zip(self.expressions, other.expressions))
        )


class Expression:
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return str(self.value)

    def __repr__(self):
        return "<{}: {!r}>".format(self.__class__.__name__, self.value)

    def __eq__(self, other):
        return type(self) == type(other) and self.value == other.value

    def validate(self, known_fields):
        return []


class WhereClause(Expression):
    def transform(self):
        """
        overriden_value = bool(value)
        value = value or self.value

        is_parenthesis = isinstance(value, Parenthesis)
        if is_parenthesis:
            value = value.args[0]

        if isinstance(value, BooleanCondition):
            join_str = "\n{} ".format(value.type.upper())
            where_str = "\n" + join_str.join(self.transform(a) for a in value.args)
            where_str = where_str.replace("\n", "\n ")
        elif overriden_value:
            where_str = str(value)
        else:
            where_str = " {}".format(value)

        if is_parenthesis:
            where_str = " ({}\n)".format(where_str)
        return where_str
        """
        return str(self.value)

    def validate(self, known_fields):
        errors = super().validate(known_fields)
        errors += self.value.validate(known_fields)
        return errors


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
            type(self) == type(other)
            and self.function_name == other.function_name
            and len(self.args) == len(other.args)
            and all(a == o for a, o in zip(self.args, other.args))
        )


class Column(Expression):
    def validate(self, known_fields):
        errors = super().validate(known_fields)
        if self.value not in known_fields:
            errors.append("The column {} was not found".format(self.value))
        return errors


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


class Boolean(Expression):
    TRUE_VALUES = (
        "true",
        "t",
        "y",
        "yes",
    )
    FALSE_VALUES = (
        "false",
        "f",
        "n",
        "no",
    )
    BOOLEAN_VALUES = TRUE_VALUES + FALSE_VALUES

    def __init__(self, value):
        assert value in self.BOOLEAN_VALUES
        if value in self.TRUE_VALUES:
            value = True
        else:
            value = False
        super().__init__(value)

    def __str__(self):
        return str(self.value).upper()


class Parenthesis(Expression):
    def __init__(self, *args):
        self.args = args

    def __str__(self):
        return "({})".format(", ".join(map(str, self.args)))

    def __repr__(self):
        return "<Parenthesis: {}>".format(", ".join(map(repr, self.args)))

    def __eq__(self, other):
        return (
            type(self) == type(other)
            and len(self.args) == len(other.args)
            and all(a == o for a, o in zip(self.args, other.args))
        )

    def validate(self, known_fields):
        errors = super().validate(known_fields)
        for a in self.args:
            errors += a.validate(known_fields)
        return errors


class Alias(Expression):
    def __init__(self, expression, alias, with_as):
        self.expression = expression
        self.alias = alias
        self.with_as = with_as

    def __str__(self):
        return "{}{}{}".format(
            self.expression, " AS " if self.with_as else " ", self.alias,
        )

    def __repr__(self):
        return "<Alias: {!r} as={} {}>".format(
            self.expression, self.with_as, self.alias
        )

    def __eq__(self, other):
        return (
            type(self) == type(other)
            and self.expression == other.expression
            and self.alias == other.alias
        )

    def validate(self, known_fields):
        errors = super().validate(known_fields)
        if isinstance(self.expression, Column):
            errors += self.expression.validate(known_fields)
        return errors


class ArithmaticOperator(Expression):
    def __init__(self, operator, *args):
        self.operator = operator
        self.args = args

    def __str__(self):
        join_str = " {} ".format(self.operator)
        return join_str.join(map(str, self.args))

    def __repr__(self):
        return "<{} {}: {}>".format(
            self.__class__.__name__, self.operator, ", ".join(map(repr, self.args))
        )

    def __eq__(self, other):
        return (
            (isinstance(other, type(self)) or isinstance(self, type(other)))
            and self.operator == other.operator
            and len(self.args) == len(other.args)
            and all(a == o for a, o in zip(self.args, other.args))
        )


class Addition(ArithmaticOperator):
    def __init__(self, *args):
        super().__init__("+", *args)


class Table(Expression):
    pass


class Condition(Expression):
    PREDICATES = ("=", ">", "<", "<=", ">=", "is")

    def __init__(self, expression, predicate, right_hand):
        super().__init__(expression)
        self.predicate = predicate
        self.right_hand = right_hand

    def __str__(self):
        return "{} {} {}".format(self.value, self.predicate.upper(), self.right_hand)

    def __repr__(self):
        return "<Condition: {!r} {} {!r}>".format(
            self.value, self.predicate, self.right_hand
        )

    def validate(self, known_fields):
        errors = super().validate(known_fields)
        errors += self.value.validate(known_fields)
        errors += self.right_hand.validate(known_fields)
        return errors


class BooleanCondition(Expression):
    PREDICATES = ("and", "or")

    def __init__(self, type, *args):
        assert type in ("and", "or")
        self.type = type
        self.args = args

    def __str__(self):
        join_str = " {} ".format(self.type.upper())
        return join_str.join(map(str, self.args))

    def __repr__(self):
        return "<BooleanCondition {}: {}>".format(
            self.type, ", ".join(map(repr, self.args))
        )

    def __eq__(self, other):
        return (
            type(self) == type(other)
            and self.type == other.type
            and len(self.args) == len(other.args)
            and all(a == o for a, o in zip(self.args, other.args))
        )
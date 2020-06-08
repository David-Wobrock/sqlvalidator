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
        group_by_clause=None,
        having_clause=None,
        order_by_clause=None,
        limit_clause=None,
        offset_clause=None,
        semi_colon=True,
    ):
        self.expressions = expressions
        self.select_all = select_all
        self.select_distinct = select_distinct
        self.select_distinct_on = select_distinct_on
        self.from_statement = from_statement
        self.where_clause = where_clause
        self.group_by_clause = group_by_clause
        self.having_clause = having_clause
        self.order_by_clause = order_by_clause
        self.limit_clause = limit_clause
        self.offset_clause = offset_clause
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
            statement_str += " {}".format(transform(self.expressions[0]))
        else:
            statement_str += "\n {}".format(
                ",\n ".join(map(transform, self.expressions))
            )

        if self.from_statement:
            if isinstance(self.from_statement, Alias):
                alias = self.from_statement
                self.from_statement = self.from_statement.expression
            else:
                alias = None

            if isinstance(self.from_statement, Parenthesis):
                from_str = "(\n{}\n)".format(
                    self.from_statement.args[0].transform(is_subquery=True)
                )
            else:
                from_str = str(self.from_statement)

            if alias:
                from_str = alias.transform(from_str)
            statement_str += "\nFROM {}".format(from_str)

        if self.where_clause:
            statement_str += "\nWHERE {}".format(transform(self.where_clause))

        if self.group_by_clause:
            statement_str += "\nGROUP BY{}".format(transform(self.group_by_clause))

        if self.having_clause:
            statement_str += "\nHAVING {}".format(transform(self.having_clause))

        if self.order_by_clause:
            statement_str += "\nORDER BY{}".format(transform(self.order_by_clause))

        if self.limit_clause:
            statement_str += "\nLIMIT {}".format(transform(self.limit_clause))

        if self.offset_clause:
            statement_str += "\nOFFSET {}".format(transform(self.offset_clause))

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

        for e in self.expressions:
            errors += e.validate(known_fields)
        if self.where_clause:
            errors += self.where_clause.validate(known_fields)
        if self.group_by_clause:
            errors += self.group_by_clause.validate(known_fields, self.expressions)
        if self.having_clause:
            errors += self.having_clause.validate(known_fields)
        if self.order_by_clause:
            errors += self.order_by_clause.validate(known_fields, self.expressions)
        if self.limit_clause:
            errors += self.limit_clause.validate(known_fields)
        if self.offset_clause:
            errors += self.offset_clause.validate(known_fields)
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
            and self.where_clause == other.where_clause
            and self.group_by_clause == other.group_by_clause
            and self.having_clause == other.having_clause
            and self.order_by_clause == other.order_by_clause
            and self.limit_clause == other.limit_clause
            and self.offset_clause == other.offset_clause
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

    @property
    def return_type(self):
        return Any


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
        if self.value.return_type != bool:
            errors.append(
                "The argument of WHERE must be type boolean, not type {}".format(
                    self.value.return_type
                )
            )
        return errors


class GroupByClause(Expression):
    def __init__(self, *args, rollup=False):
        self.args = args
        self.rollup = rollup

    def __str__(self):
        if len(self.args) > 1:
            group_by_str = "\n{}".format(",\n".join(map(str, self.args))).replace(
                "\n", "\n "
            )
        else:
            group_by_str = " " + transform(self.args[0])
        if self.rollup:
            group_by_str = " ROLLUP{}".format(group_by_str)
        return group_by_str

    def __repr__(self):
        return "<GroupByClause: {} - rollup={}>".format(
            ", ".join(map(repr, self.args)), self.rollup
        )

    def __eq__(self, other):
        return (
            type(self) == type(other)
            and len(self.args) == len(other.args)
            and all(a == o for a, o in zip(self.args, other.args))
            and self.rollup == other.rollup
        )

    def validate(self, known_fields, select_expressions):
        errors = super().validate(known_fields)
        for arg in self.args:
            while isinstance(arg, Parenthesis):
                arg = arg.args[0]
            if isinstance(arg, Integer) and (
                arg.value <= 0 or arg.value > len(select_expressions)
            ):
                errors.append(
                    "GROUP BY position {} is not in select list".format(arg.value)
                )
            elif (
                isinstance(arg, (Column, String))
                and arg.value not in known_fields
                and "*" not in known_fields
            ):
                errors.append('column "{}" does not exist'.format(arg.value))

        return errors


class HavingClause(Expression):
    def validate(self, known_fields):
        errors = super().validate(known_fields)
        errors += self.value.validate(known_fields)
        if self.value.return_type != bool:
            errors.append(
                "The argument of WHERE must be type boolean, not type {}".format(
                    self.value.return_type
                )
            )
        return errors


class OrderByClause(Expression):
    def __init__(self, *args):
        self.args = args

    def __str__(self):
        if len(self.args) > 1:
            order_by_str = "\n" + ",\n".join(map(str, self.args))
            order_by_str = order_by_str.replace("\n", "\n ")
        else:
            order_by_str = " " + transform(self.args[0])
        return order_by_str

    def __repr__(self):
        return "<OrderByClause: {}>".format(", ".join(map(repr, self.args)),)

    def __eq__(self, other):
        return (
            type(self) == type(other)
            and len(self.args) == len(other.args)
            and all(a == o for a, o in zip(self.args, other.args))
        )

    def validate(self, known_fields, select_expressions):
        errors = super().validate(known_fields)
        for arg in self.args:
            errors += arg.validate(known_fields, select_expressions)
        return errors


class OrderByItem(Expression):
    def __init__(self, expression, has_asc=False, has_desc=False):
        super().__init__(expression)
        self.has_asc = has_asc
        self.has_desc = has_desc

    def __str__(self):
        order_by_item_str = str(self.value)
        if self.has_asc:
            order_by_item_str += " ASC"
        elif self.has_desc:
            order_by_item_str += " DESC"
        return order_by_item_str

    def __repr__(self):
        return "<OrderByItem: {} has_asc={} has_desc={}>".format(
            repr(self.value), self.has_asc, self.has_desc
        )

    def __eq__(self, other):
        return (
            super().__eq__(other)
            and self.has_asc == other.has_asc
            and self.has_desc == other.has_desc
        )

    def validate(self, known_fields, select_expressions):
        errors = super().validate(known_fields)
        value = self.value
        while isinstance(value, Parenthesis):
            value = value.value

        if isinstance(value, Integer):
            if value.value <= 0 or value.value > len(select_expressions):
                errors.append(
                    "ORDER BY position {} is not in select list".format(value.value)
                )
        else:
            errors += self.value.validate(known_fields)
        return errors


class LimitClause(Expression):
    def __init__(self, limit_all, expression):
        super().__init__(expression)
        self.limit_all = limit_all

    def __str__(self):
        if self.limit_all:
            limit_str = "ALL"
        else:
            limit_str = str(self.value)
        return limit_str

    def __repr__(self):
        return "<LimitClause: {} limit_all={}>".format(repr(self.value), self.limit_all)

    def __eq__(self, other):
        return super().__eq__(other) and self.limit_all == other.limit_all

    def validate(self, known_fields):
        errors = super().validate(known_fields)
        value = self.value
        while isinstance(value, Parenthesis):
            value = value.value
        if self.value.return_type != int:
            errors.append("argument of OFFSET must not contain variables")
        else:
            if isinstance(value, Integer) and value.value < 0:
                errors.append("OFFSET must not be negative")
        return errors


class OffsetClause(Expression):
    def validate(self, known_fields):
        errors = super().validate(known_fields)
        value = self.value
        while isinstance(value, Parenthesis):
            value = value.value
        if self.value.return_type != int:
            errors.append("argument of LIMIT must be integer")
        else:
            if isinstance(value, Integer) and value.value < 0:
                errors.append("LIMIT must not be negative")
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
        if self.value not in known_fields and "*" not in known_fields:
            errors.append("The column {} was not found".format(self.value))
        return errors


class String(Expression):
    def __init__(self, value, quotes):
        super().__init__(value)
        self.quotes = quotes

    def __str__(self):
        return "{quotes}{value}{quotes}".format(quotes=self.quotes, value=self.value)

    @property
    def return_type(self):
        return str


class Integer(Expression):
    def __init__(self, value):
        super().__init__(int(value))

    def __str__(self):
        return str(self.value)

    @property
    def return_type(self):
        return int


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

    @property
    def return_type(self):
        return bool


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

    @property
    def value(self):
        if isinstance(self.args[0], Parenthesis):
            return self.args[0].value
        return self.args[0]

    def validate(self, known_fields):
        errors = super().validate(known_fields)
        for a in self.args:
            errors += a.validate(known_fields)
        return errors

    @property
    def return_type(self):
        for a in self.args:
            return a.return_type


class Alias(Expression):
    def __init__(self, expression, alias, with_as):
        self.expression = expression
        self.alias = alias
        self.with_as = with_as

    def transform(self, expression=None):
        expression = expression or self.expression
        return "{}{}{}".format(expression, " AS " if self.with_as else " ", self.alias,)

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

    @property
    def return_type(self):
        return int


class Addition(ArithmaticOperator):
    def __init__(self, *args):
        super().__init__("+", *args)


class Table(Expression):
    pass


class Condition(Expression):
    PREDICATES = ("=", ">", "<", "<=", ">=", "is", "like", "<>")

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

    @property
    def return_type(self):
        return bool


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

    def validate(self, known_fields):
        errors = super().validate(known_fields)
        for a in self.args:
            errors += a.validate(known_fields)
            if a.return_type != bool:
                errors.append(
                    "The argument of {} must be type boolean, not type {}".format(
                        self.type.upper(), a.return_type
                    )
                )

        return errors

    @property
    def return_type(self):
        return bool

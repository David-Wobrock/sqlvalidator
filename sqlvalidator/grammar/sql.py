from dataclasses import dataclass
from typing import Any, List, Optional, Set

from sqlvalidator.grammar.tokeniser import lower

DEFAULT_LINE_LENGTH = 88


def transform(obj: Any) -> str:
    if hasattr(obj, "transform"):
        return obj.transform()
    return str(obj)


@dataclass
class _FieldInfo:
    name: str
    type: type

    def __hash__(self):
        return hash(self.name)


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
                ",\n ".join(
                    map(
                        lambda s: s.replace("\n", "\n "),
                        map(transform, self.expressions),
                    )
                )
            )

        if self.from_statement:
            if isinstance(self.from_statement, Alias):
                alias = self.from_statement
                from_statement = self.from_statement.expression
            else:
                alias = None
                from_statement = self.from_statement

            if isinstance(from_statement, Parenthesis):
                if isinstance(from_statement.args[0], SelectStatement):
                    inner_from_str = from_statement.args[0].transform(is_subquery=True)
                else:
                    inner_from_str = " " + transform(from_statement.args[0]).replace(
                        "\n", "\n "
                    )
                from_str = f"(\n{inner_from_str}\n)"
            else:
                from_str = transform(from_statement)

            if alias:
                from_str = alias.transform(from_str)
            statement_str += "\nFROM {}".format(from_str)

        if self.where_clause:
            statement_str += "\nWHERE{}".format(transform(self.where_clause))

        if self.group_by_clause:
            statement_str += "\nGROUP {}BY{}".format(
                "EACH " if self.group_by_clause.group_each_by else "",
                transform(self.group_by_clause),
            )

        if self.having_clause:
            statement_str += "\nHAVING{}".format(transform(self.having_clause))

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

    def validate(self, known_fields: Optional[Set[_FieldInfo]] = None) -> list:
        errors = []
        known_fields = known_fields or set()
        if hasattr(self.from_statement, "known_fields"):
            known_fields = known_fields | self.from_statement.known_fields

        for e in self.expressions:
            errors += e.validate(known_fields)
        if self.from_statement:
            errors += self.from_statement.validate(known_fields=set())
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
    def known_fields(self) -> Set[_FieldInfo]:
        fields = set()
        for e in self.expressions:
            if isinstance(e, Column):
                fields.add(_FieldInfo(e.value, e.return_type))
            elif isinstance(e, Alias):
                if isinstance(e.alias, Column):
                    fields.add(_FieldInfo(e.alias.value, e.return_type))
                else:
                    fields.add(_FieldInfo(e.alias, e.return_type))

        if self.from_statement:
            if isinstance(self.from_statement, Parenthesis) and isinstance(
                self.from_statement.args[0], SelectStatement
            ):
                subquery_known_fields = self.from_statement.args[0].known_fields
                if any(f.name == "*" for f in fields) and not any(
                    f.name == "*" for f in subquery_known_fields
                ):
                    fields = {f for f in fields if f.name != "*"}
                    fields |= subquery_known_fields

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
            and self.semi_colon == other.semi_colon
        )

    def __repr__(self):
        return """<{}:
  Expressions: {!r}
  Select All: {!r} - Select Distinct: {!r} - Select Distinct On: {!r}
  From: {!r}
  Where: {!r}
  Group By: {!r}
  Having: {!r}
  Order By: {!r}
  Limit: {!r}
  Offset: {!r}
  Semi Colon: {!r}
>
        """.format(
            self.__class__.__name__,
            self.expressions,
            self.select_all,
            self.select_distinct,
            self.select_distinct_on,
            self.from_statement,
            self.where_clause,
            self.group_by_clause,
            self.having_clause,
            self.order_by_clause,
            self.limit_clause,
            self.offset_clause,
            self.semi_colon,
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

    def validate(self, known_fields: Set[_FieldInfo]) -> list:
        return []

    @property
    def return_type(self):
        return object

    def resolve_return_type(self, known_fields):
        matching_fields = [f for f in known_fields if f.name == transform(self)]
        if matching_fields:
            return matching_fields[0].type
        return self.return_type


class WhereClause(Expression):
    def transform(self):
        transformed_value = transform(self.value)
        if isinstance(self.value, Parenthesis) and "\n" in transformed_value:
            return " (\n " + transform(self.value.args[0]).replace("\n", "\n ") + "\n)"
        if "\n" in transformed_value:
            return "\n " + transformed_value.replace("\n", "\n ")
        return " " + transformed_value

    def validate(self, known_fields: Set[_FieldInfo]) -> list:
        errors = super().validate(known_fields)
        errors += self.value.validate(known_fields)
        value_type = self.value.resolve_return_type(known_fields)
        if value_type not in (bool, object):
            errors.append(
                "The argument of WHERE must be type boolean, not type {}".format(
                    value_type.__name__
                )
            )
        return errors

    def __eq__(self, other):
        return type(self) == type(other) and self.value == other.value


class GroupByClause(Expression):
    def __init__(self, *args, rollup=False):
        self.args = args
        self.rollup = rollup
        self.group_each_by = False

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
            and self.group_each_by == other.group_each_by
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
                and (
                    not any(f.name == arg.value for f in known_fields)
                    and arg.value
                    not in [e.alias for e in select_expressions if isinstance(e, Alias)]
                )
                and not any(f.name == "*" for f in known_fields)
            ):
                fields_without_alias = [
                    f for f in known_fields if f.name.split(".", 1)[-1] == arg.value
                ]
                if len(fields_without_alias) > 1:
                    errors.append('column "{}" is ambiguous'.format(self.value))
                elif len(fields_without_alias) == 0:
                    errors.append('column "{}" does not exist'.format(arg.value))

        return errors


class HavingClause(Expression):
    def __str__(self):
        transformed_value = transform(self.value)
        if isinstance(self.value, Parenthesis) and "\n" in transformed_value:
            return " (\n " + transform(self.value.args[0]).replace("\n", "\n ") + "\n)"
        if "\n" in transformed_value:
            return "\n " + transformed_value.replace("\n", "\n ")
        return " " + transformed_value

    def validate(self, known_fields):
        errors = super().validate(known_fields)
        errors += self.value.validate(known_fields)
        value_type = self.value.resolve_return_type(known_fields)
        if value_type not in (bool, object):
            errors.append(
                "The argument of HAVING must be type boolean, not type {}".format(
                    value_type.__name__
                )
            )
        return errors


class OrderByClause(Expression):
    def __init__(self, *args):
        self.args = args

    def transform(self, allow_linebreak=True):
        if len(self.args) > 1:
            if allow_linebreak:
                order_by_str = "\n" + ",\n".join(map(str, self.args))
                order_by_str = order_by_str.replace("\n", "\n ")
            else:
                order_by_str = " " + ", ".join(map(str, self.args))
        else:
            order_by_str = " " + transform(self.args[0])
        return order_by_str

    def __repr__(self):
        return "<OrderByClause: {}>".format(
            ", ".join(map(repr, self.args)),
        )

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
        if value.return_type != int or not isinstance(value, Integer):
            errors.append("argument of LIMIT must not contain variables")
        else:
            if isinstance(value, Integer) and value.value < 0:
                errors.append("LIMIT must not be negative")
        return errors


class OffsetClause(Expression):
    def validate(self, known_fields):
        errors = super().validate(known_fields)
        value = self.value
        while isinstance(value, Parenthesis):
            value = value.value
        if value.return_type != int or not isinstance(value, Integer):
            errors.append("argument of OFFSET must be integer")
        else:
            if isinstance(value, Integer) and value.value < 0:
                errors.append("OFFSET must not be negative")
        return errors


class WithQuery(Expression):
    def __init__(self, name: str, statement: SelectStatement):
        self.name = name
        # todo: column name, for recursivity
        self.statement = statement

    def __str__(self):
        return "{} AS (\n{}\n)".format(
            self.name, self.statement.transform(is_subquery=True)
        )

    def __eq__(self, other):
        return (
            type(self) == type(other)
            and self.name == other.name
            and self.statement == other.statement
        )


class WithStatement(Expression):
    def __init__(self, with_queries: List[WithQuery], select_statement):
        # todo: recursive
        self.with_queries = with_queries
        self.select_statement = select_statement

    def transform(self):
        return "WITH {}\n{}".format(
            ",\n".join(map(transform, self.with_queries)),
            transform(self.select_statement),
        )

    def __eq__(self, other):
        return (
            type(self) == type(other)
            and len(self.with_queries) == len(other.with_queries)
            and all(a == o for a, o in zip(self.with_queries, other.with_queries))
            and self.select_statement == other.select_statement
        )


class FunctionCall(Expression):
    def __init__(self, function_name, *args):
        self.function_name = function_name
        self.args = args

    def __str__(self):
        transformed_args = [transform(arg) for arg in self.args]
        with_newlines = (
            any("\n" in arg for arg in transformed_args)
            or len(", ".join(transformed_args)) > DEFAULT_LINE_LENGTH
        )

        function_str = self.function_name.upper() + "("
        if with_newlines:
            function_str += "\n "
            function_str += (
                ",\n ".join(arg.replace("\n", "\n ") for arg in transformed_args)
                + "\n)"
            )
        else:
            function_str += ", ".join(transformed_args) + ")"
        return function_str

    def validate(self, known_fields):
        errors = super().validate(known_fields)
        for a in self.args:
            errors += a.validate(known_fields)
        return errors

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


class CastFunctionCall(FunctionCall):
    def __init__(self, column, cast_type):
        super().__init__("cast", column, "AS", cast_type)

    def __str__(self):
        return "{}({} AS {})".format(
            self.function_name.upper(),
            transform(self.args[0]),
            transform(self.args[2]),
        )


class CountFunctionCall(FunctionCall):
    def __init__(self, *args, distinct=False):
        super().__init__("count", *args)
        self.distinct = distinct

    def __str__(self):
        return "{}({}{})".format(
            self.function_name.upper(),
            "DISTINCT " if self.distinct else "",
            ", ".join(map(transform, self.args)),
        )

    def __eq__(self, other):
        return super().__eq__(other) and self.distinct == other.distinct


class ArrayAggFunctionCall(FunctionCall):
    def __init__(
        self,
        column,
        distinct=False,
        ignore_nulls=False,
        respect_nulls=False,
        order_bys=None,
        limit=None,
    ):
        super().__init__("array_agg", column)
        self.distinct = distinct
        assert not (ignore_nulls and respect_nulls)
        self.ignore_nulls = ignore_nulls
        self.respect_nulls = respect_nulls
        self.order_bys = order_bys
        self.limit = limit

    def __str__(self):
        array_agg_str = "{}(".format(self.function_name.upper())
        if self.distinct:
            array_agg_str += "DISTINCT "

        array_agg_str += transform(self.args[0])

        if self.ignore_nulls:
            array_agg_str += " IGNORE NULLS"
        elif self.respect_nulls:
            array_agg_str += " RESPECT NULLS"

        if self.order_bys:
            array_agg_str += " ORDER BY{}".format(
                self.order_bys.transform(allow_linebreak=False)
            )

        if self.limit:
            array_agg_str += " LIMIT {}".format(self.limit)

        return array_agg_str + ")"


class FilteredFunctionCall(Expression):
    def __init__(self, function_call: FunctionCall, filter_condition):
        self.function_call = function_call
        self.filter_condition = filter_condition

    def __str__(self):
        return "{} FILTER (WHERE {})".format(
            transform(self.function_call), transform(self.filter_condition)
        )

    def __eq__(self, other):
        return (
            type(self) == type(other)
            and self.function_call == other.function_call
            and self.filter_condition == other.filter_condition
        )

    def validate(self, known_fields):
        errors = super().validate(known_fields)
        errors += self.function_call.validate(known_fields)
        errors += self.filter_condition.validate(known_fields)
        return errors


class AnalyticsClause(Expression):
    def __init__(self, function, partition_by, order_by, frame_clause):
        self.function = function
        self.partition_by = partition_by
        self.order_by = order_by
        self.frame_clause = frame_clause

    def __str__(self):
        analytics_str = "{} OVER (".format(transform(self.function))
        if self.partition_by:
            analytics_str += "\n PARTITION BY"
            if len(self.partition_by) > 1:
                analytics_str += "\n  " + ",\n  ".join(
                    map(transform, self.partition_by)
                )
            else:
                analytics_str += " " + transform(self.partition_by[0])
        if self.order_by:
            analytics_str += "\n ORDER BY{}".format(
                transform(self.order_by).replace("\n", "\n ")
            )
        if self.frame_clause:
            if "\n" in analytics_str:
                analytics_str += "\n "
            analytics_str += transform(self.frame_clause)

        analytics_str += "\n)" if "\n" in analytics_str else ")"
        return analytics_str

    def __eq__(self, other):
        return (
            type(self) == type(other)
            and self.function == other.function
            and (
                (self.partition_by is None and other.partition_by is None)
                or (
                    len(self.partition_by) == len(other.partition_by)
                    and all(
                        a == o for a, o in zip(self.partition_by, other.partition_by)
                    )
                )
            )
            and self.order_by == other.order_by
            and self.frame_clause == other.frame_clause
        )

    def __repr__(self):
        return """<{}:
  Function: {!r}
  Partition By: {!r}
  Order By: {!r}
  Frame Clause: {!r}
""".format(
            self.__class__.__name__,
            self.function,
            self.partition_by,
            self.order_by,
            self.frame_clause,
        )

    def validate(self, known_fields):
        errors = super().validate(known_fields)
        errors += self.function.validate(known_fields)
        if self.partition_by:
            for partition in self.partition_by:
                errors += partition.validate(known_fields)
        if self.order_by:
            errors += self.order_by.validate(known_fields, None)
        return errors


class WindowFrameClause(Expression):
    def __init__(self, rows_range, frame):
        self.rows_range = rows_range
        self.frame = frame

    def __str__(self):
        return "{} {}".format(self.rows_range.upper(), self.frame.upper())

    def __repr__(self):
        return """<{}:
  Row Range: {!r}
  Frame: {!r}
""".format(
            self.__class__.__name__,
            self.rows_range,
            self.frame,
        )

    def __eq__(self, other):
        return (
            type(self) == type(other)
            and self.rows_range == other.rows_range
            and self.frame == other.frame
        )


class Column(Expression):
    KEYWORDS = (
        "_table_suffix",
        "_partitiondate",
        "nfc",
        "nfkc",
        "nfd",
        "nfkd",
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
    )

    def __str__(self):
        if self.value in self.KEYWORDS:
            return self.value.upper()
        return str(self.value)

    def validate(self, known_fields):
        errors = super().validate(known_fields)
        if (
            not any(f.name == self.value for f in known_fields)
            and self.value != "*"
            and not any(f.name == "*" for f in known_fields)
        ):
            fields_without_alias = [
                f for f in known_fields if f.name.split(".", 1)[-1] == self.value
            ]
            if len(fields_without_alias) > 1:
                errors.append('column "{}" is ambiguous'.format(self.value))
            elif len(fields_without_alias) == 0:
                errors.append("The column {} was not found".format(self.value))
        return errors


class ChainedColumns(Expression):
    def __init__(self, *args):
        self.columns = args

    def __str__(self):
        return ".".join(map(transform, self.columns))

    def __repr__(self):
        return "<ChainedColumns: {}>".format(".".join(map(repr, self.columns)))

    def __eq__(self, other):
        return (
            type(self) == type(other)
            and len(self.columns) == len(other.columns)
            and all(a == o for a, o in zip(self.columns, other.columns))
        )

    @property
    def return_type(self):
        return self.columns[-1].return_type

    def validate(self, known_fields):
        errors = super().validate(known_fields)
        full_value = str(self)
        alias = ".".join(map(transform, self.columns[:-1]))
        last_value = self.columns[-1]
        if (
            not any(f.name == full_value for f in known_fields)
            and not any(f.name == f"{alias}.*" for f in known_fields)
        ) and not any(f.name == "*" for f in known_fields):
            errors.append(f"The column {last_value} was not found in alias {alias}")
        return errors


class Type(Expression):
    VALUES = ("int", "float", "day", "month", "timestamp", "int64", "string", "date")

    def __str__(self):
        return self.value.upper()


class DatePartExtraction(Expression):
    PARTS = (
        "microsecond",
        "second",
        "minute",
        "hour",
        "day",
        "week",
        "month",
        "quarter",
        "year",
        "second_microsecond",
        "minute_microsecond",
        "minute_second",
        "hour_microsecond",
        "hour_second",
        "hour_minute",
        "day_microsecond",
        "day_second",
        "day_minute",
        "day_hour",
        "year_month",
        "dayofmonth",
        "dayofweek",
        "dayofyear",
        "date",
    )

    def __init__(self, part, date_expression):
        super().__init__(date_expression)
        self.part = part

    def __str__(self):
        return "{} FROM {}".format(self.part.upper(), transform(self.value))


class String(Expression):
    QUOTES = ("'", '"', "`")
    PREFIXES = ("r",)

    def __init__(self, value, quotes, prefix=None):
        super().__init__(value)
        self.quotes = quotes
        self.prefix = prefix

    def __str__(self):
        return "{prefix}{quotes}{value}{quotes}".format(
            quotes=self.quotes, value=self.value, prefix=self.prefix or ""
        )

    def __repr__(self):
        return "<{}: {!r} quotes={!r} prefix={!r}>".format(
            self.__class__.__name__, self.value, self.quotes, self.prefix
        )

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


class Float(Expression):
    def __init__(self, value):
        super().__init__(float(value))

    def __str__(self):
        return str(self.value)

    @property
    def return_type(self):
        return float


class Null(Expression):
    VALUES = ("null",)

    def __init__(self):
        super().__init__(None)

    def __str__(self):
        return "NULL"

    @property
    def return_type(self):
        return type(None)


class Boolean(Expression):
    TRUE_VALUES = (
        "true",
        "yes",
    )
    FALSE_VALUES = (
        "false",
        "no",
    )
    BOOLEAN_VALUES = TRUE_VALUES + FALSE_VALUES

    def __init__(self, value):
        value = lower(value)
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
        return "({})".format(
            ", ".join(
                "\n" + a.transform(is_subquery=True) + "\n"
                if isinstance(a, SelectStatement)
                else transform(a)
                for a in self.args
            )
        )

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
    def known_fields(self) -> Set[_FieldInfo]:
        if hasattr(self.args[0], "known_fields"):
            return self.args[0].known_fields
        return set()

    @property
    def return_type(self):
        for a in self.args:
            return a.return_type


class Array(Expression):
    def __init__(self, *args):
        self.args = args

    def __str__(self):
        return "[{}]".format(", ".join(map(transform, self.args)))

    def __repr__(self):
        return "<Array: {}>".format(", ".join(map(repr, self.args)))

    def __eq__(self, other):
        return (
            type(self) == type(other)
            and len(self.args) == len(other.args)
            and all(a == o for a, o in zip(self.args, other.args))
        )


class Alias(Expression):
    def __init__(self, expression, alias, with_as):
        self.expression = expression
        self.alias = alias
        self.with_as = with_as

    def transform(self, expression=None):
        expression = expression or self.expression
        return "{}{}{}".format(
            transform(expression),
            " AS " if self.with_as else " ",
            transform(self.alias),
        )

    def __repr__(self):
        return "<Alias: {!r} as={} {!r}>".format(
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
        errors += self.expression.validate(known_fields)
        return errors

    @property
    def return_type(self):
        return self.expression.return_type

    @property
    def known_fields(self) -> Set[_FieldInfo]:
        return {
            _FieldInfo("{}.{}".format(transform(self.alias), f.name), f.type)
            for f in self.expression.known_fields
        }


class Index(Expression):
    def __init__(self, expression, indices):
        super().__init__(expression)
        self.indices = indices

    def __str__(self):
        return "{}[{}]".format(
            transform(self.value), ", ".join(map(transform, self.indices))
        )

    def __repr__(self):
        return "<Index: {!r} indices={!r}>".format(
            self.value, ", ".join(map(repr, self.indices))
        )


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
        if any(isinstance(a, float) for a in self.args):
            return float
        return int


class Addition(ArithmaticOperator):
    def __init__(self, *args):
        super().__init__("+", *args)


class BitwiseOperation(Expression):
    OPERATORS = ("&", "|", "^", "||", "<<", ">>", "#")

    def __init__(self, expression, predicate, right_hand):
        super().__init__(expression)
        self.predicate = predicate
        self.right_hand = right_hand

    def __str__(self):
        return "{} {} {}".format(
            transform(self.value), self.predicate, transform(self.right_hand)
        )

    def __repr__(self):
        return "<BitwiseOperation: {!r} {} {!r}>".format(
            self.value, self.predicate, self.right_hand
        )


class Table(Expression):
    def __init__(self, value, in_square_brackets=False):
        super().__init__(value)
        self.in_square_brackets = in_square_brackets

    def __str__(self):
        table_str = transform(self.value)
        if self.in_square_brackets:
            table_str = f"[{table_str}]"
        return table_str

    @property
    def known_fields(self) -> Set[_FieldInfo]:
        return {_FieldInfo("*", type=object)}


class Unnest(Expression):
    def __init__(self, unnest_expression, with_offset, with_offset_as, offset_alias):
        # unnest_expression: can be functiion call or alias of function call
        super().__init__(unnest_expression)
        self.with_offset = with_offset
        self.with_offset_as = with_offset_as
        self.offset_alias = offset_alias

    def __str__(self):
        unnest_str = transform(self.value)
        if self.with_offset:
            unnest_str += " WITH OFFSET"
            if self.offset_alias:
                if self.with_offset_as:
                    unnest_str += " AS"
                unnest_str += f" {self.offset_alias}"
        return unnest_str

    def __eq__(self, other):
        return (
            (isinstance(other, type(self)) or isinstance(self, type(other)))
            and self.value == other.value
            and self.with_offset == other.with_offset
            and self.with_offset_as == other.with_offset_as
            and self.offset_alias == other.offset_alias
        )


class Join(Expression):
    VALUES = ("join", "inner", "left", "right", "full", "cross", "outer", ",", "each")

    def __init__(self, join_type, left_from, right_from, on, using):
        self.join_type = join_type
        self.left_from = left_from
        self.right_from = right_from
        self.on = on
        self.using = using

    def __str__(self):
        right_from = self.right_from
        num_parenthesis = 0

        alias = None
        if isinstance(right_from, Alias):
            alias = right_from
            right_from = right_from.expression

        while isinstance(right_from, Parenthesis):
            right_from = right_from.args[0]
            num_parenthesis += 1

        if isinstance(right_from, SelectStatement):
            right_element = right_from.transform(is_subquery=True)
        else:
            right_element = transform(right_from)

        if num_parenthesis:
            right_element = "\n" + right_element
            if not isinstance(right_from, SelectStatement):
                right_element = right_element.replace("\n", "\n ")
            right_element = " {}{}\n{}".format(
                "(" * num_parenthesis,
                right_element,
                ")" * num_parenthesis,
            )
        else:
            right_element = " " + right_element

        if alias:
            right_element = "{}{} {}".format(
                right_element, " AS" if alias.with_as else "", alias.alias
            )

        left_from = self.left_from

        alias = None
        if isinstance(left_from, Alias):
            alias = left_from
            left_from = left_from.expression

        num_parenthesis = 0
        while isinstance(left_from, Parenthesis):
            left_from = left_from.args[0]
            num_parenthesis += 1

        if isinstance(left_from, SelectStatement):
            left_element = left_from.transform(is_subquery=True)
        else:
            left_element = transform(left_from)

        if num_parenthesis:
            left_element = "\n" + left_element
            if not isinstance(left_from, SelectStatement):
                left_element = left_element.replace("\n", "\n ")
            left_element = "{}{}\n{}".format(
                "(" * num_parenthesis,
                left_element,
                ")" * num_parenthesis,
            )
        if alias:
            left_element = "{}{} {}".format(
                left_element, " AS" if alias.with_as else "", alias.alias
            )

        join_type_str = (
            "\n{}".format(self.join_type.upper()) if self.join_type != "," else ","
        )
        join_str = "{}{}{}".format(
            left_element,
            join_type_str,
            right_element,
        )
        if self.on:
            join_str += "\nON{}".format(transform(self.on))
        elif self.using:
            join_str += "\nUSING{}".format(transform(self.using))
        return join_str

    def __eq__(self, other):
        return (
            type(self) == type(other)
            and self.join_type == other.join_type
            and self.left_from == other.left_from
            and self.right_from == other.right_from
            and self.on == other.on
            and self.using == other.using
        )

    def __repr__(self):
        return """<{}:
  Join Type: {!r}
  Left part: {!r}
  Right part: {!r}
  On: {!r}
  Using {!r}
""".format(
            self.__class__.__name__,
            self.join_type,
            self.left_from,
            self.right_from,
            self.on,
            self.using,
        )

    def validate(self, known_fields: Set[_FieldInfo]) -> list:
        errors = super().validate(known_fields)
        if self.join_type not in ("CROSS JOIN", ",") and not (self.using or self.on):
            errors.append("Missing ON or USING for join")
        return errors

    @property
    def known_fields(self) -> Set[_FieldInfo]:
        known_fields = set()
        if isinstance(self.left_from, Alias):
            left_alias = self.left_from.alias
            for field in self.left_from.expression.known_fields:
                known_fields.add(_FieldInfo(left_alias + "." + field.name, field.type))
        else:
            known_fields |= self.left_from.known_fields

        if isinstance(self.right_from, Alias):
            right_alias = self.right_from.alias
            for field in self.right_from.expression.known_fields:
                known_fields.add(
                    _FieldInfo(
                        right_alias + "." + field.name,
                        field.type,
                    )
                )
        else:
            known_fields |= self.right_from.known_fields

        return known_fields


class CombinedQueries(Expression):
    SET_OPERATORS = ("union", "intersect", "except", "all")

    def __init__(self, set_operator, left_query, right_query):
        self.set_operator = set_operator
        self.left_query = left_query
        self.right_query = right_query

    def __str__(self):
        left_query = transform(self.left_query)
        right_query = transform(self.right_query)
        if isinstance(self.right_query, Table):
            right_query = " " + right_query
        else:
            right_query = "\n" + right_query

        return "{}\n{}{}".format(left_query, self.set_operator.upper(), right_query)

    def __eq__(self, other):
        return (
            type(self) == type(other)
            and self.set_operator == other.set_operator
            and self.left_query == other.left_query
            and self.right_query == other.right_query
        )

    def __repr__(self):
        return """<{}:
  Set Operator: {!r}
  Left query: {!r}
  Right query: {!r}
""".format(
            self.__class__.__name__,
            self.set_operator,
            self.left_query,
            self.right_query,
        )


class OnClause(Expression):
    def __str__(self):
        transformed_value = transform(self.value)
        if isinstance(self.value, Parenthesis) and "\n" in transformed_value:
            return " (\n " + transform(self.value.args[0]).replace("\n", "\n ") + "\n)"
        if "\n" in transformed_value:
            return "\n " + transformed_value.replace("\n", "\n ")
        return " " + transformed_value


class UsingClause(Expression):
    def __str__(self):
        transformed_value = transform(self.value)
        if isinstance(self.value, Parenthesis) and "\n" in transformed_value:
            return " (\n " + transform(self.value.args[0]).replace("\n", "\n ") + "\n)"
        if "\n" in transformed_value:
            return "\n " + transformed_value.replace("\n", "\n ")
        return " " + transformed_value


class Condition(Expression):
    PREDICATES = (
        "=",
        ">",
        "<",
        "<=",
        ">=",
        "!=",
        "is",
        "like",
        "<>",
        "in",
        "not",
        "contains",
    )

    def __init__(self, expression, predicate, right_hand):
        super().__init__(expression)
        self.predicate = predicate
        self.right_hand = right_hand

    def __str__(self):
        return "{} {} {}".format(
            transform(self.value), self.predicate.upper(), transform(self.right_hand)
        )

    def __repr__(self):
        return "<Condition: {!r} {} {!r}>".format(
            self.value, self.predicate, self.right_hand
        )

    def __eq__(self, other):
        return (
            type(self) == type(other)
            and self.value == other.value
            and self.predicate == other.predicate
            and self.right_hand == other.right_hand
        )

    def validate(self, known_fields):
        errors = super().validate(known_fields)
        errors += self.value.validate(known_fields)
        if self.predicate.lower() == "between":
            errors += self.right_hand.validate(known_fields, is_between_predicate=True)
        else:
            errors += self.right_hand.validate(known_fields)
        return errors

    @property
    def return_type(self):
        return bool


class BooleanCondition(Expression):
    PREDICATES = ("and", "or")

    def __init__(self, type, *args):
        assert type.lower() in ("and", "or")
        self.type = type
        self.args = args

    def transform(self, with_newline=False):
        join_str = " {} ".format(self.type.upper())
        transformed_condition = join_str.join(map(transform, self.args))
        if len(transformed_condition) < DEFAULT_LINE_LENGTH and with_newline is False:
            return transformed_condition

        join_str = "\n{} ".format(self.type.upper())
        transformed_args = []
        for a in self.args:
            if isinstance(a, BooleanCondition):
                transformed_a = a.transform(with_newline=True)
            elif isinstance(a, Parenthesis):
                transformed_a = transform(a.args[0])
                if "\n" in transformed_a:
                    transformed_a = "(\n " + transformed_a.replace("\n", "\n ") + "\n)"
                else:
                    transformed_a = f"({transformed_a})"
            else:
                transformed_a = transform(a)
            transformed_args.append(transformed_a)

        return join_str.join(transformed_args)

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

    def validate(self, known_fields, is_between_predicate=False):
        errors = super().validate(known_fields)
        for a in self.args:
            errors += a.validate(known_fields)
            if not is_between_predicate:
                a_type = a.resolve_return_type(known_fields)
                if a_type not in (bool, object):
                    errors.append(
                        "The argument of {} must be type boolean, not type {}".format(
                            self.type.upper(), a_type.__name__
                        )
                    )

        return errors

    @property
    def return_type(self):
        return bool


class Negation(Expression):
    PREDICATE = "not"

    def __init__(self, expression):
        super().__init__(expression)

    def __str__(self):
        negation = "NOT"
        if not isinstance(self.value, Parenthesis):
            negation += " "
        return negation + transform(self.value)

    @property
    def return_type(self):
        return bool


class SelectAllClause(Expression):
    KEYWORD = ""

    def __init__(self, expression, args):
        super().__init__(expression)
        self.args = args

    def __repr__(self):
        return "<{}: {!r} args: {!r}>".format(
            self.__class__.__name__, self.value, self.args
        )

    def __str__(self):
        except_str = "{} {} (".format(transform(self.value), self.KEYWORD)
        if len(self.args) > 1:
            except_str += "\n {}\n".format(",\n ".join(map(transform, self.args)))
        elif except_str:
            except_str += transform(self.args[0])
        return except_str + ")"


class ExceptClause(SelectAllClause):
    KEYWORD = "EXCEPT"


class ReplaceClause(SelectAllClause):
    KEYWORD = "REPLACE"

    def validate(self, known_fields: Set[_FieldInfo]) -> list:
        errors = super().validate(known_fields)
        for arg in self.args:
            errors += arg.alias.validate(known_fields)
        return errors


class Case(Expression):
    def __init__(self, expression, when_then, else_expression):
        super().__init__(expression)
        self.when_then = when_then
        self.else_expression = else_expression

    def __str__(self):
        case_str = "CASE"
        if self.value:
            case_str += " {}".format(transform(self.value))

        case_str += "\n "
        when_then_block_str = []
        for when, then in self.when_then:
            when_then_str = "WHEN"
            transformed_when = transform(when)
            if isinstance(when, Parenthesis) and "\n" in transformed_when:
                when_then_str += (
                    " (\n  " + transform(when.args[0]).replace("\n", "\n  ") + "\n )\n "
                )
            elif "\n" in transformed_when:
                when_then_str += "\n  " + transformed_when.replace("\n", "\n  ") + "\n "
            else:
                when_then_str += " " + transformed_when + " "

            when_then_str += f"THEN {then}"
            when_then_block_str.append(when_then_str)

        case_str += "\n ".join(when_then_block_str)

        if self.else_expression:
            case_str += "\n ELSE {}".format(transform(self.else_expression))
        case_str += "\nEND"
        return case_str

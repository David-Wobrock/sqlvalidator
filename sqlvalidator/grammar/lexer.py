from typing import Any, Optional, Tuple

from sqlvalidator.grammar.sql import (
    Alias,
    AnalyticsClause,
    ArithmaticOperator,
    Array,
    ArrayAggFunctionCall,
    BitwiseOperation,
    Boolean,
    BooleanCondition,
    Case,
    CastFunctionCall,
    ChainedColumns,
    Column,
    CombinedQueries,
    Condition,
    DatePartExtraction,
    ExceptClause,
    Expression,
    FunctionCall,
    GroupByClause,
    HavingClause,
    Index,
    Integer,
    Join,
    LimitClause,
    Negation,
    Null,
    OffsetClause,
    OnClause,
    OrderByClause,
    OrderByItem,
    Parenthesis,
    SelectStatement,
    String,
    Table,
    Type,
    Unnest,
    UsingClause,
    WhereClause,
    WindowFrameClause,
)
from sqlvalidator.grammar.tokeniser import (
    get_tokens_until_closing_parenthesis,
    get_tokens_until_not_in,
    get_tokens_until_one_of,
    lower,
)


class ParsingError(Exception):
    pass


class SQLStatementParser:
    @staticmethod
    def parse(tokens):
        next_token = next(tokens)
        if lower(next_token) == "select":
            return SelectStatementParser.parse(tokens)
        raise ParsingError


class SelectStatementParser:
    keywords = (";", "from", "where", "group", "having", "order", "limit", "offset")

    @classmethod
    def parse(cls, tokens):
        first_expression_token = None
        next_token = next(tokens)

        select_all = select_distinct = False
        select_distinct_on = None
        if lower(next_token) == "all":
            select_all = True
        elif lower(next_token) == "distinct":
            select_distinct = True
            next_token = next(tokens)
            if lower(next_token) == "on":
                next(tokens)  # Consume parenthesis
                distinct_on_tokens = get_tokens_until_closing_parenthesis(tokens)
                select_distinct_on = ExpressionListParser.parse(
                    iter(distinct_on_tokens)
                )
            else:
                first_expression_token = next_token
        else:
            first_expression_token = next_token

        expression_tokens, next_token = get_tokens_until_one_of(
            tokens, cls.keywords, first_token=first_expression_token
        )
        expressions = ExpressionListParser.parse(iter(expression_tokens))

        if lower(next_token) == "from":
            expression_tokens, next_token = get_tokens_until_one_of(
                tokens,
                ["where", "group", "having", "order", "limit", "offset", ";"],
                keep=[("with", "offset")],
            )
            from_statement = FromStatementParser.parse(iter(expression_tokens))
        else:
            from_statement = None

        if lower(next_token) == "where":
            where_clause, next_token = WhereClauseParser.parse(tokens)
        else:
            where_clause = None

        if lower(next_token) == "group":
            next_token = next(tokens, None)
            if not lower(next_token) == "by":
                raise ParsingError("Missing BY after GROUP")
            expression_tokens, next_token = get_tokens_until_one_of(
                tokens, ["having", "order", "limit", "offset", ";"]
            )
            group_by_clause = GroupByParser.parse(iter(expression_tokens))
        else:
            group_by_clause = None

        if lower(next_token) == "having":
            having_clause, next_token = HavingClauseParser.parse(tokens)
        else:
            having_clause = None

        if lower(next_token) == "order":
            next_token = next(tokens, None)
            if not lower(next_token) == "by":
                raise ParsingError("Missing BY after ORDER")
            expression_tokens, next_token = get_tokens_until_one_of(
                tokens, ["limit", "offset", ";"]
            )
            order_by_clause = OrderByParser.parse(iter(expression_tokens))
        else:
            order_by_clause = None

        if lower(next_token) == "limit":
            expression_tokens, next_token = get_tokens_until_one_of(
                tokens, ["offset", ";"]
            )
            limit_clause = LimitClauseParser.parse(iter(expression_tokens))
        else:
            limit_clause = None

        if lower(next_token) == "offset":
            expression_tokens, next_token = get_tokens_until_one_of(tokens, [";"])
            offset_clause = OffsetClauseParser.parse(iter(expression_tokens))
        else:
            offset_clause = None

        semi_colon = bool(next_token and next_token == ";")
        return SelectStatement(
            select_all=select_all,
            select_distinct=select_distinct,
            select_distinct_on=select_distinct_on,
            expressions=expressions,
            from_statement=from_statement,
            where_clause=where_clause,
            group_by_clause=group_by_clause,
            having_clause=having_clause,
            order_by_clause=order_by_clause,
            limit_clause=limit_clause,
            offset_clause=offset_clause,
            semi_colon=semi_colon,
        )


class FromStatementParser:
    @staticmethod
    def parse(tokens):
        next_token = next(tokens)
        if next_token == "(":
            argument_tokens = get_tokens_until_closing_parenthesis(tokens)
            try:
                argument = SQLStatementParser.parse(iter(argument_tokens))
            except ParsingError:
                argument = FromStatementParser.parse(iter(argument_tokens))
            expression = Parenthesis(argument)
            next_token = next(tokens, None)
        elif next_token == "'" or next_token == '"' or next_token == "`":
            expression = Table(StringParser.parse(tokens, next_token))
            next_token = next(tokens, None)
        elif next_token == "[":
            argument_tokens, next_token = get_tokens_until_one_of(
                tokens, stop_words=["]"]
            )
            table, _ = ExpressionParser.parse(iter(argument_tokens))
            expression = Table(table, in_square_brackets=True)
            assert next_token == "]", next_token
            next_token = next(tokens, None)
        else:
            if lower(next_token) == "unnest":
                expression = UnnestParser.parse(tokens)
                next_token = next(tokens, None)
            else:
                argument_tokens, next_token = get_tokens_until_one_of(
                    tokens,
                    stop_words=Join.VALUES + CombinedQueries.SET_OPERATORS,
                    first_token=next_token,
                )
                expression = Table(ExpressionParser.parse(iter(argument_tokens))[0])

        if (
            next_token is not None
            and lower(next_token) not in Join.VALUES
            and lower(next_token) not in CombinedQueries.SET_OPERATORS
        ):
            if lower(next_token) == "as":
                with_as = True
                alias = next(tokens)
            else:
                with_as = False
                alias = next_token
            expression = Alias(expression, alias, with_as)
            next_token = next(tokens, None)

        while lower(next_token) in CombinedQueries.SET_OPERATORS:
            left_expr = expression
            expression_tokens, next_token = get_tokens_until_not_in(
                tokens, CombinedQueries.SET_OPERATORS, first_token=next_token
            )
            set_operator = SetOperatorTypeParser.parse(iter(expression_tokens))
            expression_tokens, next_token = get_tokens_until_one_of(
                tokens,
                CombinedQueries.SET_OPERATORS,
                first_token=next_token,
            )
            if lower(expression_tokens[0]) == "select":
                right_expr = SelectStatementParser.parse(iter(expression_tokens[1:]))
            else:
                right_expr = FromStatementParser.parse(iter(expression_tokens))
            expression = CombinedQueries(set_operator, left_expr, right_expr)

            if (
                next_token is not None
                and lower(next_token) not in CombinedQueries.SET_OPERATORS
            ):
                if lower(next_token) == "as":
                    with_as = True
                    alias = next(tokens)
                else:
                    with_as = False
                    alias = next_token
                expression = Alias(expression, alias, with_as)
                next_token = next(tokens, None)

        while lower(next_token) in Join.VALUES:
            left_expr = expression
            expression_tokens, next_token = get_tokens_until_not_in(
                tokens, Join.VALUES, first_token=next_token
            )
            join_type = JoinTypeParser.parse(iter(expression_tokens))

            if join_type in ("CROSS JOIN", ","):
                expression_tokens, next_token = [next_token] + list(tokens), None
            else:
                expression_tokens, next_token = get_tokens_until_one_of(
                    tokens, ("on", "using"), first_token=next_token
                )
            right_expr = FromStatementParser.parse(iter(expression_tokens))
            on = None
            using = None
            on_or_using = next_token
            expression_tokens, next_token = get_tokens_until_one_of(
                tokens,
                Join.VALUES,
            )
            if lower(on_or_using) == "on":
                expression, _ = ExpressionParser.parse(iter(expression_tokens))
                on = OnClause(expression)
            elif lower(on_or_using) == "using":
                expressions, _ = ExpressionParser.parse(iter(expression_tokens))
                using = UsingClause(expressions)
            elif join_type not in ("CROSS JOIN", ","):
                raise ParsingError("Missing ON or USING for join")

            expression = Join(join_type, left_expr, right_expr, on=on, using=using)

            if next_token is not None and lower(next_token) not in Join.VALUES:
                if lower(next_token) == "as":
                    with_as = True
                    alias = next(tokens)
                else:
                    with_as = False
                    alias = next_token
                expression = Alias(expression, alias, with_as)
                next_token = next(tokens, None)

        return expression


class JoinTypeParser:
    @staticmethod
    def parse(tokens):
        # TODO: assert known join types
        return " ".join(tokens).upper()


class UnnestParser:
    @staticmethod
    def parse(tokens):
        next_token = next(tokens)
        assert next_token == "("
        argument_tokens = get_tokens_until_closing_parenthesis(tokens)
        arguments = ExpressionListParser.parse(iter(argument_tokens))
        expression = FunctionCall("unnest", *arguments)

        next_token = next(tokens, None)
        if (
            next_token is not None
            and lower(next_token) not in Join.VALUES
            and lower(next_token) not in CombinedQueries.SET_OPERATORS
            and lower(next_token) != "with"
        ):
            if lower(next_token) == "as":
                with_as = True
                alias = next(tokens)
            else:
                with_as = False
                alias = next_token
            expression = Alias(expression, alias, with_as)
            next_token = next(tokens, None)

        with_offset = False
        with_offset_as = False
        offset_alias = None

        if lower(next_token) == "with":
            next_token = next(tokens)
            assert lower(next_token) == "offset", next_token
            with_offset = True

            next_token = next(tokens, None)
            if (
                next_token is not None
                and lower(next_token) not in Join.VALUES
                and lower(next_token) not in CombinedQueries.SET_OPERATORS
            ):
                if lower(next_token) == "as":
                    with_offset_as = True
                    offset_alias = next(tokens)
                else:
                    offset_alias = next_token

        return Unnest(
            expression,
            with_offset=with_offset,
            with_offset_as=with_offset_as,
            offset_alias=offset_alias,
        )


class SetOperatorTypeParser:
    @staticmethod
    def parse(tokens):
        return " ".join(tokens).upper()


class WhereClauseParser:
    @staticmethod
    def parse(tokens):
        expression, next_token = ExpressionParser.parse(
            tokens,
            can_alias=False,
            until_one_of=("group", "having", "order", "limit", "offset", ";"),
        )
        return WhereClause(expression), next_token


class GroupByParser:
    @staticmethod
    def parse(tokens):
        next_token = next(tokens)
        if lower(next_token) == "rollup":
            rollup = True
            next_token = None
        else:
            rollup = False
        expression_tokens, _ = get_tokens_until_one_of(
            tokens, [], first_token=next_token
        )
        expressions = ExpressionListParser.parse(iter(expression_tokens))
        return GroupByClause(*expressions, rollup=rollup)


class HavingClauseParser:
    @staticmethod
    def parse(tokens):
        expression, next_token = ExpressionParser.parse(
            tokens, can_alias=False, until_one_of=["order", "limit", "offset", ";"]
        )
        return HavingClause(expression), next_token


class OrderByParser:
    @staticmethod
    def parse(tokens):
        expressions = []

        expression_tokens, next_token = get_tokens_until_one_of(tokens, [","])
        expression = OrderByItemParser.parse(iter(expression_tokens))
        expressions.append(expression)
        while next_token:
            expression_tokens, next_token = get_tokens_until_one_of(tokens, [","])
            expression = OrderByItemParser.parse(iter(expression_tokens))
            expressions.append(expression)

        return OrderByClause(*expressions)


class OrderByItemParser:
    @staticmethod
    def parse(tokens):
        expression_tokens, next_token = get_tokens_until_one_of(tokens, ["asc", "desc"])
        expression, _ = ExpressionParser.parse(iter(expression_tokens))
        if lower(next_token) == "asc":
            has_asc = True
            has_desc = False
        elif lower(next_token) == "desc":
            has_asc = False
            has_desc = True
        else:
            has_asc = False
            has_desc = False

        return OrderByItem(expression, has_asc=has_asc, has_desc=has_desc)


class LimitClauseParser:
    @staticmethod
    def parse(tokens):
        next_token = next(tokens)
        if lower(next_token) == "all":
            limit_all = True
            expression = None
        else:
            limit_all = False
            expression_tokens, next_token = get_tokens_until_one_of(
                tokens, [], first_token=next_token
            )
            expression, _ = ExpressionParser.parse(iter(expression_tokens))
        return LimitClause(limit_all, expression)


class OffsetClauseParser:
    @staticmethod
    def parse(tokens):
        expression, _ = ExpressionParser.parse(tokens)
        return OffsetClause(expression)


class ExpressionListParser:
    @staticmethod
    def parse(tokens, can_be_type=False):
        next_token = next(tokens, None)

        expressions = []
        expression_tokens = []
        count_parenthesis = 0
        count_square_brackets = 0
        while next_token is not None:
            expression_tokens.append(next_token)
            if next_token == "(":
                count_parenthesis += 1
            elif next_token == ")":
                count_parenthesis -= 1
            elif next_token == "[":
                count_square_brackets += 1
            elif next_token == "]":
                count_square_brackets -= 1

            next_token = next(tokens, None)
            if next_token is None or (
                next_token == ","
                and count_parenthesis == 0
                and count_square_brackets == 0
            ):
                expression, _ = ExpressionParser.parse(
                    iter(expression_tokens), can_be_type=can_be_type
                )
                expressions.append(expression)
                expression_tokens = []
                next_token = next(tokens, None)
        return expressions


class ExpressionParser:
    @staticmethod
    def parse(
        tokens,
        is_right_hand=False,
        can_be_type=False,
        can_alias=True,
        until_one_of=None,
    ) -> Tuple[Expression, Any]:
        until_one_of = until_one_of or []

        main_token = next(tokens)
        next_token = None

        if main_token in String.QUOTES:
            expression = StringParser.parse(tokens, main_token)
        elif main_token.isdigit():
            expression = Integer(main_token)
        elif lower(main_token) in Boolean.BOOLEAN_VALUES:
            expression = Boolean(main_token)
        elif lower(main_token) in Null.VALUES:
            expression = Null()
        elif lower(main_token) == Negation.PREDICATE:
            rest_expression, next_token = ExpressionParser.parse(
                tokens,
                is_right_hand=True,
                until_one_of=until_one_of,
            )
            expression = Negation(rest_expression)
        elif main_token == "(":
            argument_tokens = get_tokens_until_closing_parenthesis(tokens)
            arguments = ExpressionListParser.parse(iter(argument_tokens))
            expression = Parenthesis(*arguments)
        elif main_token == "[":
            argument_tokens, next_token = get_tokens_until_one_of(
                tokens, stop_words=["]"]
            )
            assert next_token == "]", next_token
            arguments = ExpressionListParser.parse(iter(argument_tokens))
            expression = Array(*arguments)
            next_token = next(tokens, None)
        elif lower(main_token) == "case":
            argument_tokens, next_token = get_tokens_until_one_of(tokens, ["end"])
            assert lower(next_token) == "end"
            next_token = next(tokens, None)
            expression = CaseParser.parse(iter(argument_tokens))
        elif lower(main_token) == "select":
            argument_tokens, next_token = get_tokens_until_one_of(tokens, [])
            next_token = next(tokens, None)
            expression = SelectStatementParser.parse(iter(argument_tokens))
        else:
            expression = None

        if next_token is None:
            next_token = next(tokens, None)

        # Expressions that need the next_token to be read
        if expression is None:
            if next_token is not None and next_token == "(":
                if lower(main_token) == "cast":
                    column_tokens, next_token = get_tokens_until_one_of(
                        tokens, stop_words=["as"]
                    )
                    column, _ = ExpressionParser.parse(
                        iter(column_tokens),
                        is_right_hand=True,
                        until_one_of=until_one_of,
                    )
                    assert lower(next_token) == "as", next_token
                    next_token = next(tokens)
                    cast_type = Type(next_token)
                    expression = CastFunctionCall(column, cast_type)
                    next_token = next(tokens)
                    assert lower(next_token) == ")", next_token
                elif lower(main_token) == "array_agg":
                    next_token = next(tokens)
                    if lower(next_token) == "distinct":
                        distinct = True
                        first_token = None
                    else:
                        distinct = False
                        first_token = next_token

                    column_tokens, next_token = get_tokens_until_one_of(
                        tokens,
                        stop_words=[")", "ignore", "respects", "order", "limit"],
                        first_token=first_token,
                    )
                    column, _ = ExpressionParser.parse(
                        iter(column_tokens), until_one_of=until_one_of
                    )

                    ignore_nulls = respect_nulls = False
                    if lower(next_token) == "ignore":
                        next_token = next(tokens)
                        assert lower(next_token) == "nulls"
                        ignore_nulls = True
                        next_token = next(tokens)
                    elif lower(next_token) == "respect":
                        next_token = next(tokens)
                        assert lower(next_token) == "nulls"
                        respect_nulls = True
                        next_token = next(tokens)

                    if lower(next_token) == "order":
                        next_token = next(tokens)
                        assert lower(next_token) == "by"
                        expression_tokens, next_token = get_tokens_until_one_of(
                            tokens, ["limit", ")"]
                        )
                        order_bys = OrderByParser.parse(iter(expression_tokens))
                    else:
                        order_bys = None

                    limit = None
                    if lower(next_token) == "limit":
                        next_token = next(tokens)
                        limit = int(next_token)
                        next_token = next(tokens)

                    assert lower(next_token) == ")", next_token
                    expression = ArrayAggFunctionCall(
                        column=column,
                        distinct=distinct,
                        ignore_nulls=ignore_nulls,
                        respect_nulls=respect_nulls,
                        order_bys=order_bys,
                        limit=limit,
                    )
                else:
                    argument_tokens = get_tokens_until_closing_parenthesis(tokens)
                    arguments_can_be_type = (
                        "," in argument_tokens or lower(main_token) == "if"
                    )
                    arguments = ExpressionListParser.parse(
                        iter(argument_tokens), can_be_type=arguments_can_be_type
                    )
                    expression = FunctionCall(main_token, *arguments)
                next_token = next(tokens, None)
            elif (
                next_token is not None
                and lower(main_token) in DatePartExtraction.PARTS
                and lower(next_token) == "from"
            ):
                rest_expression, next_token = ExpressionParser.parse(
                    tokens, until_one_of=until_one_of
                )
                expression = DatePartExtraction(main_token, rest_expression)
            elif lower(main_token) in Type.VALUES and can_be_type:
                expression = Type(main_token)
            elif next_token is not None and next_token == "[":
                argument_tokens, next_token = get_tokens_until_one_of(
                    tokens, stop_words=["]"]
                )
                arguments = ExpressionListParser.parse(iter(argument_tokens))
                expression = Index(
                    Column(main_token), arguments
                )  # left item will not always be a column
                next_token = next(tokens, None)
            elif next_token is not None and main_token == "-" and next_token.isdigit():
                expression = Integer(-int(next_token))
                next_token = next(tokens, None)
            elif (
                lower(main_token) in String.PREFIXES
                and next_token is not None
                and lower(next_token) in String.QUOTES
            ):
                expression = StringParser.parse(
                    tokens, start_quote=next_token, prefix=main_token
                )
            else:
                expression = Column(main_token)

        if lower(next_token) == "over":
            opening_parenthesis = next(tokens, None)
            if opening_parenthesis != "(":
                raise ParsingError("expected '('")

            argument_tokens = iter(get_tokens_until_closing_parenthesis(tokens))
            argument_next_token = next(argument_tokens, None)
            if lower(argument_next_token) == "partition":
                argument_next_token = next(argument_tokens, None)
                if not argument_next_token or lower(argument_next_token) != "by":
                    raise ParsingError("Missing BY after PARTITION")
                expression_tokens, argument_next_token = get_tokens_until_one_of(
                    argument_tokens, ["order", "rows", "range"]
                )
                partition_by = ExpressionListParser.parse(iter(expression_tokens))
            else:
                partition_by = None

            if lower(argument_next_token) == "order":
                argument_next_token = next(argument_tokens, None)
                if not argument_next_token or lower(argument_next_token) != "by":
                    raise ParsingError("Missing BY after ORDER")
                expression_tokens, argument_next_token = get_tokens_until_one_of(
                    argument_tokens, ["rows", "range"]
                )
                order_by = OrderByParser.parse(iter(expression_tokens))
            else:
                order_by = None

            if lower(argument_next_token) in ("rows", "range"):
                rows_range = argument_next_token
                expression_tokens, _ = get_tokens_until_one_of(argument_tokens, [])
                frame_clause: Optional[WindowFrameClause] = WindowFrameClause(
                    rows_range, " ".join(expression_tokens)
                )
            else:
                frame_clause = None

            expression = AnalyticsClause(
                expression,
                partition_by=partition_by,
                order_by=order_by,
                frame_clause=frame_clause,
            )
            next_token = next(tokens, None)

        if next_token and next_token in ("+", "-", "*", "/"):
            left_hand = expression
            symbol = next_token
            right_hand, next_token = ExpressionParser.parse(
                tokens, is_right_hand=True, until_one_of=until_one_of
            )
            expression = ArithmaticOperator(symbol, left_hand, right_hand)

        if next_token == ".":
            right_hand, next_token = ExpressionParser.parse(
                tokens, is_right_hand=True, until_one_of=until_one_of
            )
            expression = ChainedColumns(expression, right_hand)

        if is_right_hand:
            return expression, next_token

        if lower(next_token) in Condition.PREDICATES:
            symbol = next_token
            if lower(next_token) == "is":
                next_next_token = next(tokens)
                if lower(next_next_token) == "not":
                    symbol = "is not"
                else:
                    tokens, _ = get_tokens_until_one_of(
                        tokens, [], first_token=next_next_token
                    )
                    tokens = iter(tokens)

            right_hand, next_token = ExpressionParser.parse(
                tokens, is_right_hand=True, until_one_of=until_one_of
            )
            expression = Condition(expression, symbol, right_hand)
        elif lower(next_token) == "between":
            symbol = next_token
            right_hand_left, next_token = ExpressionParser.parse(
                tokens, is_right_hand=True, until_one_of=until_one_of
            )
            if lower(next_token) != "and":
                raise ParsingError("expected AND")
            right_hand_right, next_token = ExpressionParser.parse(
                tokens, is_right_hand=True, until_one_of=until_one_of
            )
            right_hand = BooleanCondition(
                "and",
                right_hand_left,
                right_hand_right,
            )
            expression = Condition(expression, symbol, right_hand)
        elif next_token in BitwiseOperation.OPERATORS:
            operator = next_token
            right_hand, next_token = ExpressionParser.parse(
                tokens, is_right_hand=True, until_one_of=until_one_of
            )
            expression = BitwiseOperation(expression, operator, right_hand)

        if lower(next_token) in BooleanCondition.PREDICATES:
            left_hand = expression
            symbol = next_token
            right_hand, next_token = ExpressionParser.parse(
                tokens, until_one_of=until_one_of
            )
            expression = BooleanCondition(symbol, left_hand, right_hand)

        if lower(next_token) == "except":
            opening_parenthesis = next(tokens, None)
            if opening_parenthesis != "(":
                raise ParsingError("expected '('")
            argument_tokens = get_tokens_until_closing_parenthesis(tokens)
            arguments = ExpressionListParser.parse(iter(argument_tokens))
            expression = ExceptClause(expression, arguments)
            next_token = next(tokens, None)

        if (
            next_token is not None
            and next_token != ")"
            and next_token != "'"
            and next_token != '"'
            and next_token != "`"
            and next_token != ";"
            and lower(next_token) not in until_one_of
            and can_alias
        ):
            if lower(next_token) == "as":
                with_as = True
                alias, _ = ExpressionParser.parse(
                    tokens, is_right_hand=True, until_one_of=until_one_of
                )
            else:
                with_as = False
                alias = next_token
            return Alias(expression, alias, with_as), next(tokens, None)
        return expression, next_token


class StringParser:
    @staticmethod
    def parse(tokens, start_quote, prefix=None):
        string_content = next(tokens, None)
        if string_content == start_quote:
            end_quote = string_content
            string_content = ""
        else:
            end_quote = next(tokens)

        string_expression = String(string_content, quotes=start_quote, prefix=prefix)
        if start_quote != end_quote:
            raise ValueError("Did not find ending quote {}".format(start_quote))
        return string_expression


class CaseParser:
    @staticmethod
    def parse(tokens):
        next_token = next(tokens)
        if lower(next_token) == "when":
            expression = None
        else:
            expressions_tokens, next_token = get_tokens_until_one_of(
                tokens, ["when"], first_token=next_token
            )
            expression, _ = ExpressionParser.parse(iter(expressions_tokens))

        when_then = []
        else_expression = None
        while next_token:
            if lower(next_token) == "when":
                expressions_tokens, _ = get_tokens_until_one_of(tokens, ["then"])
                when_expression, _ = ExpressionParser.parse(iter(expressions_tokens))
                expressions_tokens, next_token = get_tokens_until_one_of(
                    tokens, ["when", "else"]
                )
                then_expression, _ = ExpressionParser.parse(iter(expressions_tokens))
                when_then.append((when_expression, then_expression))
            elif lower(next_token) == "else":
                expressions_tokens, next_token = get_tokens_until_one_of(tokens, [])
                else_expression, _ = ExpressionParser.parse(iter(expressions_tokens))

        return Case(expression, when_then, else_expression)

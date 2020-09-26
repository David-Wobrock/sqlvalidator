from sqlvalidator.grammar.sql import (
    SelectStatement,
    FunctionCall,
    Column,
    Type,
    Alias,
    String,
    Integer,
    Parenthesis,
    Table,
    ArithmaticOperator,
    Condition,
    BooleanCondition,
    Boolean,
    WhereClause,
    GroupByClause,
    HavingClause,
    OrderByClause,
    OrderByItem,
    LimitClause,
    OffsetClause,
    Null,
    Join,
    OnClause,
    UsingClause,
    ExceptClause,
    AnalyticsClause,
    WindowFrameClause,
    Case,
    Index,
)
from sqlvalidator.grammar.tokeniser import (
    get_tokens_until_one_of,
    get_tokens_until_closing_parenthesis,
    get_tokens_until_not_in,
)


class ParsingError(Exception):
    pass


class SQLStatementParser:
    @staticmethod
    def parse(tokens):
        next_token = next(tokens)
        if next_token == "select":
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
        if next_token == "all":
            select_all = True
        elif next_token == "distinct":
            select_distinct = True
            next_token = next(tokens)
            if next_token == "on":
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

        if next_token == "from":
            expression_tokens, next_token = get_tokens_until_one_of(
                tokens, ["where", "group", "having", "order", "limit", "offset", ";"]
            )
            from_statement = FromStatementParser.parse(iter(expression_tokens))
        else:
            from_statement = None

        if next_token == "where":
            expression_tokens, next_token = get_tokens_until_one_of(
                tokens, ["group", "having", "order", "limit", "offset", ";"]
            )
            where_clause = WhereClauseParser.parse(iter(expression_tokens))
        else:
            where_clause = None

        if next_token == "group":
            next_token = next(tokens, None)
            if not next_token == "by":
                raise ParsingError("Missing BY after GROUP")
            expression_tokens, next_token = get_tokens_until_one_of(
                tokens, ["having", "order", "limit", "offset", ";"]
            )
            group_by_clause = GroupByParser.parse(iter(expression_tokens))
        else:
            group_by_clause = None

        if next_token == "having":
            expression_tokens, next_token = get_tokens_until_one_of(
                tokens, ["order", "limit", "offset", ";"]
            )
            having_clause = HavingClauseParser.parse(iter(expression_tokens))
        else:
            having_clause = None

        if next_token == "order":
            next_token = next(tokens, None)
            if not next_token == "by":
                raise ParsingError("Missing BY after ORDER")
            expression_tokens, next_token = get_tokens_until_one_of(
                tokens, ["limit", "offset", ";"]
            )
            order_by_clause = OrderByParser.parse(iter(expression_tokens))
        else:
            order_by_clause = None

        if next_token == "limit":
            expression_tokens, next_token = get_tokens_until_one_of(
                tokens, ["offset", ";"]
            )
            limit_clause = LimitClauseParser.parse(iter(expression_tokens))
        else:
            limit_clause = None

        if next_token == "offset":
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
        elif next_token == "'" or next_token == '"' or next_token == "`":
            expression = Table(StringParser.parse(tokens, next_token))
        else:
            if next_token == "unnest":
                next_next_token = next(tokens)
                assert next_next_token == "("
                argument_tokens = get_tokens_until_closing_parenthesis(tokens)
                arguments = ExpressionListParser.parse(iter(argument_tokens))
                expression = FunctionCall(next_token, *arguments)
            else:
                expression = Table(next_token)

        next_token = next(tokens, None)
        if next_token is not None and next_token not in Join.VALUES:
            if next_token == "as":
                with_as = True
                alias = next(tokens)
            else:
                with_as = False
                alias = next_token
            expression = Alias(expression, alias, with_as)
            next_token = next(tokens, None)

        while next_token in Join.VALUES:
            left_expr = expression
            expression_tokens, next_token = get_tokens_until_not_in(
                tokens, Join.VALUES, first_token=next_token
            )
            join_type = JoinTypeParser.parse(iter(expression_tokens))
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
            if on_or_using == "on":
                expression = ExpressionParser.parse(iter(expression_tokens))
                on = OnClause(expression)
            elif on_or_using == "using":
                expressions = ExpressionParser.parse(iter(expression_tokens))
                using = UsingClause(expressions)
            else:
                raise ParsingError("Missing ON or USING for join")

            expression = Join(join_type, left_expr, right_expr, on=on, using=using)

            if next_token is not None and next_token not in Join.VALUES:
                if next_token == "as":
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


class WhereClauseParser:
    @staticmethod
    def parse(tokens):
        expression = ExpressionParser.parse(tokens)
        return WhereClause(expression)


class GroupByParser:
    @staticmethod
    def parse(tokens):
        next_token = next(tokens)
        if next_token == "rollup":
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
        expression = ExpressionParser.parse(tokens)
        return HavingClause(expression)


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
        expression = ExpressionParser.parse(iter(expression_tokens))
        if next_token == "asc":
            has_asc = True
            has_desc = False
        elif next_token == "desc":
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
        if next_token == "all":
            limit_all = True
            expression = None
        else:
            limit_all = False
            expression_tokens, next_token = get_tokens_until_one_of(
                tokens, [], first_token=next_token
            )
            expression = ExpressionParser.parse(iter(expression_tokens))
        return LimitClause(limit_all, expression)


class OffsetClauseParser:
    @staticmethod
    def parse(tokens):
        expression = ExpressionParser.parse(tokens)
        return OffsetClause(expression)


class ExpressionListParser:
    @staticmethod
    def parse(tokens):
        next_token = next(tokens, None)

        expressions = []
        expression_tokens = []
        count_parenthesis = 0
        while next_token is not None:
            expression_tokens.append(next_token)
            if next_token == "(":
                count_parenthesis += 1
            elif next_token == ")":
                count_parenthesis -= 1
            next_token = next(tokens, None)
            if next_token is None or (next_token == "," and count_parenthesis == 0):
                expressions.append(ExpressionParser.parse(iter(expression_tokens)))
                expression_tokens = []
                next_token = next(tokens, None)
        return expressions


class ExpressionParser:
    @staticmethod
    def parse(tokens, is_right_hand=False):
        main_token = next(tokens)
        next_token = None

        if main_token in String.QUOTES:
            expression = StringParser.parse(tokens, main_token)
        elif main_token.isdigit():
            expression = Integer(main_token)
        elif main_token in Boolean.BOOLEAN_VALUES:
            expression = Boolean(main_token)
        elif main_token in Null.VALUES:
            expression = Null()
        elif main_token in Type.VALUES:
            expression = Type(main_token)
        elif main_token == "(":
            argument_tokens = get_tokens_until_closing_parenthesis(tokens)
            arguments = ExpressionListParser.parse(iter(argument_tokens))
            expression = Parenthesis(*arguments)
        elif main_token == "case":
            argument_tokens, next_token = get_tokens_until_one_of(tokens, ["end"])
            assert next_token == "end"
            next_token = next(tokens, None)
            expression = CaseParser.parse(iter(argument_tokens))
        elif main_token == "select":
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
                argument_tokens = get_tokens_until_closing_parenthesis(tokens)
                arguments = ExpressionListParser.parse(iter(argument_tokens))
                expression = FunctionCall(main_token, *arguments)
                next_token = next(tokens, None)
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
                main_token in String.PREFIXES
                and next_token is not None
                and next_token in String.QUOTES
            ):
                expression = StringParser.parse(
                    tokens, start_quote=next_token, prefix=main_token
                )
            else:
                expression = Column(main_token)

        if next_token == "over":
            opening_parenthesis = next(tokens, None)
            if opening_parenthesis != "(":
                raise ParsingError("expected '('")

            argument_tokens = iter(get_tokens_until_closing_parenthesis(tokens))
            argument_next_token = next(argument_tokens, None)
            if argument_next_token == "partition":
                argument_next_token = next(argument_tokens, None)
                if not argument_next_token or argument_next_token != "by":
                    raise ParsingError("Missing BY after PARTITION")
                expression_tokens, argument_next_token = get_tokens_until_one_of(
                    argument_tokens, ["order", "rows", "range"]
                )
                partition_by = ExpressionListParser.parse(iter(expression_tokens))
            else:
                partition_by = None

            if argument_next_token == "order":
                argument_next_token = next(argument_tokens, None)
                if not argument_next_token or argument_next_token != "by":
                    raise ParsingError("Missing BY after ORDER")
                expression_tokens, argument_next_token = get_tokens_until_one_of(
                    argument_tokens, ["rows", "range"]
                )
                order_by = OrderByParser.parse(iter(expression_tokens))
            else:
                order_by = None

            if argument_next_token in ("rows", "range"):
                rows_range = argument_next_token
                expression_tokens, _ = get_tokens_until_one_of(argument_tokens, [])
                frame_clause = WindowFrameClause(
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
            right_hand, next_token = ExpressionParser.parse(tokens, is_right_hand=True)
            expression = ArithmaticOperator(symbol, left_hand, right_hand)

        if is_right_hand:
            return expression, next_token

        if next_token in Condition.PREDICATES:
            symbol = next_token
            if next_token == "is":
                next_next_token = next(tokens)
                if next_next_token == "not":
                    symbol = "is not"
                else:
                    tokens, _ = get_tokens_until_one_of(
                        tokens, [], first_token=next_next_token
                    )
                    tokens = iter(tokens)

            right_hand, next_token = ExpressionParser.parse(tokens, is_right_hand=True)
            expression = Condition(expression, symbol, right_hand)
        elif next_token == "between":
            symbol = next_token
            right_hand_left, next_token = ExpressionParser.parse(
                tokens, is_right_hand=True
            )
            if next_token != "and":
                raise ParsingError("expected AND")
            right_hand_right, next_token = ExpressionParser.parse(
                tokens, is_right_hand=True
            )
            right_hand = BooleanCondition(
                "and",
                right_hand_left,
                right_hand_right,
            )
            expression = Condition(expression, symbol, right_hand)

        if next_token in BooleanCondition.PREDICATES:
            left_hand = expression
            symbol = next_token
            right_hand = ExpressionParser.parse(tokens)
            expression = BooleanCondition(symbol, left_hand, right_hand)
            next_token = next(tokens, None)

        if next_token == "except":
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
        ):
            if next_token == "as":
                with_as = True
                alias, _ = ExpressionParser.parse(tokens, is_right_hand=True)
            else:
                with_as = False
                alias = next_token
            return Alias(expression, alias, with_as)
        return expression


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
        if next_token == "when":
            expression = None
        else:
            expressions_tokens, next_token = get_tokens_until_one_of(
                tokens, ["when"], first_token=next_token
            )
            expression = ExpressionParser.parse(iter(expressions_tokens))

        when_then = []
        else_expression = None
        while next_token:
            if next_token == "when":
                expressions_tokens, _ = get_tokens_until_one_of(tokens, ["then"])
                when_expression = ExpressionParser.parse(iter(expressions_tokens))
                expressions_tokens, next_token = get_tokens_until_one_of(
                    tokens, ["when", "else"]
                )
                then_expression = ExpressionParser.parse(iter(expressions_tokens))
                when_then.append((when_expression, then_expression))
            elif next_token == "else":
                expressions_tokens, next_token = get_tokens_until_one_of(tokens, [])
                else_expression = ExpressionParser.parse(iter(expressions_tokens))

        return Case(expression, when_then, else_expression)

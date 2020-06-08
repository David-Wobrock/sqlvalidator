from sqlvalidator.grammar.sql import (
    SelectStatement,
    FunctionCall,
    Column,
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
)
from sqlvalidator.grammar.tokeniser import (
    get_tokens_until_one_of,
    get_tokens_until_closing_parenthesis,
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
            argument = SQLStatementParser.parse(iter(argument_tokens))
            expression = Parenthesis(argument)
        elif next_token == "'" or next_token == '"' or next_token == "`":
            expression = Table(StringParser.parse(tokens, next_token))
        else:
            expression = Table(next_token)

        next_token = next(tokens, None)
        if next_token is not None:
            if next_token == "as":
                with_as = True
                alias = next(tokens)
            else:
                with_as = False
                alias = next_token
            expression = Alias(expression, alias, with_as)
        return expression


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

        if main_token == "'" or main_token == '"' or main_token == "`":
            expression = StringParser.parse(tokens, main_token)
        elif main_token.isdigit():
            expression = Integer(main_token)
        elif main_token in Boolean.BOOLEAN_VALUES:
            expression = Boolean(main_token)
        elif main_token == "(":
            argument_tokens = get_tokens_until_closing_parenthesis(tokens)
            arguments = ExpressionListParser.parse(iter(argument_tokens))
            expression = Parenthesis(*arguments)
        else:
            expression = None

        next_token = next(tokens, None)

        # Expressions that need the next_token to be read
        if expression is None:
            if next_token is not None and next_token == "(":
                argument_tokens = get_tokens_until_closing_parenthesis(tokens)
                arguments = ExpressionListParser.parse(iter(argument_tokens))
                expression = FunctionCall(main_token, *arguments)
                next_token = next(tokens, None)
            elif next_token is not None and main_token == "-" and next_token.isdigit():
                expression = Integer(-int(next_token))
                next_token = next(tokens, None)
            else:
                expression = Column(main_token)

        if next_token and next_token in ("+", "-", "*", "/"):
            left_hand = expression
            symbol = next_token
            right_hand, next_token = ExpressionParser.parse(tokens, is_right_hand=True)
            expression = ArithmaticOperator(symbol, left_hand, right_hand)

        if is_right_hand:
            return expression, next_token

        if next_token in Condition.PREDICATES:
            symbol = next_token
            right_hand, next_token = ExpressionParser.parse(tokens, is_right_hand=True)
            expression = Condition(expression, symbol, right_hand)

        if next_token in BooleanCondition.PREDICATES:
            left_hand = expression
            symbol = next_token
            right_hand = ExpressionParser.parse(tokens)
            expression = BooleanCondition(symbol, left_hand, right_hand)
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
                alias = next(tokens)
            else:
                with_as = False
                alias = next_token
            return Alias(expression, alias, with_as)
        return expression


class StringParser:
    @staticmethod
    def parse(tokens, start_quote):
        string_content = next(tokens, None)
        string_expression = String(string_content, quotes=start_quote)
        end_quote = next(tokens)
        if start_quote != end_quote:
            raise ValueError("Did not find ending quote {}".format(start_quote))
        return string_expression

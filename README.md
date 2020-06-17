# sqlvalidator

[![Travis](https://travis-ci.org/David-Wobrock/sqlvalidator.svg?branch=master)](https://travis-ci.org/David-Wobrock/sqlvalidator)
[![PyPI](https://img.shields.io/pypi/v/sqlvalidator.svg)](https://pypi.python.org/pypi/sqlvalidator/)

SQL queries formatting, syntactic and semantic validation

Work In Progress!

## Command line usage

For formatting SQL:

_sql.py_
```
def fun():
    return "select col1, column2 from table"  # sqlformat
```

Command line:
```
$ sqlvalidator --format sql.py
reformatted sql.py (1 changed SQL)
1 file reformatted (1 changed SQL queries).
```

_sql.py_
```
def fun():
    return """
SELECT
 col1,
 column2
FROM table
"""  # sqlformat

```

The `sqlformat` comment is required to indicated to `sqlvalidator` that this string should be formatted.

One can verify also that the file would be reformatted or not:
```
$ sqlvalidator --check-format sql.py
would reformat sql.py (1 changed SQL)
1 file would be reformatted (1 changed SQL queries).

$ sqlvalidator --format sql.py
reformatted sql.py (1 changed SQL)
1 file reformatted (1 changed SQL queries).
```

```
$ sqlvalidator --check-format sql.py
No file would be reformatted.

$ sqlvalidator --format sql.py
No file reformatted.
```

`--check-format` won't write the file back and just return a status code:
* Status code 0 means nothing would change.
* Status code 1 means some files would reformatted.


## API

### Formatting

```python
import sqlvalidator

formatted_sql = sqlvalidator.format_sql("SELECT * FROM table")
```

### Validation

```python
import sqlvalidator

sql_query = sqlvalidator.parse("SELECT * from table")

if not sql_query.is_valid():
    print(sql_query.errors)
```

**Warning**: only limited test cases are currently handled by the validation

_Details_:

To be implemented yet, but should become the main added-value of this lib.

Ideally, this package should provide a basic SQL validation:
* not using a missing column
* existing functions
* correct aggregations
* schemaless (not assume that table names and columns in those exist)
* types correctness in functions

(only on SELECT-statements)

### Internals

#### Testing

```
pytest
```

#### Publishing

* `python3 setup.py sdist bdist_wheel --universal`
* `twine upload dist/sqlvalidator-X.Y.Z-py2.py3-none-any.whl dist/sqlvalidator-X.Y.Z.tar.gz`

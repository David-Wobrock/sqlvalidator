# sqlvalidator

SQL queries formatting (and soon basic schema less validation)

## Formatting

Formatting can be used in 2 ways:
* formatting Python files that contain SQL strings tagged with `# sqlformat` from the command line:

`sqlvalidator --format myfile.py` or `sqlvalidator --format myproject/`

* formatting Python strings that represent SQL:

`sqlvalidator.format_sql("SELECT * FROM table")`

Both output the same formatted string for the same input SQL.

One can verify that all files are correctly formatted using
`sqlvalidator --check-format pyfile.py`

Which won't write the file back and just return a status code.
Status code 0 means nothing would change.
Status code 1 means some files would reformatted.

## Validation

To be implemented yet, but should become the main added-value of this lib.

Suggested API:
```python
import sqlvalidator

sql_query = sqlvalidator.parse("SELECT * from table")

if not sql_query.is_valid():
    print(sql_query.errors)
```

Ideally, this package should provide a basic SQL validation:
* not using a missing column
* existing functions
* correct aggregations
* schema-less (not assume that table names and columns in those exist)
* types correctness in functions

(only on SELECT-statements)

More advanced features:
* depending on the backend (standard SQL, postgresql, BigQuery, Legacy BigQuery...)
* Flexible internal SQL representation to do advanced validation
* With provided schema (to validate that columns exist)

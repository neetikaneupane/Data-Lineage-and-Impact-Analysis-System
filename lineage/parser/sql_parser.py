import os
import sqlglot
import sqlglot.expressions as exp


def parse_sql_file(filepath: str) -> dict:
    with open(filepath, "r") as f:
        sql = f.read()

    filename = os.path.basename(filepath)
    statements = sqlglot.parse(sql, dialect="postgres")

    result = {
        "file": filename,
        "output_table": None,
        "input_tables": [],
        "column_mappings": []
    }

    for statement in statements:
        if not statement:
            continue

        # extract output table
        if isinstance(statement, (exp.Create, exp.Insert)):
            output = _extract_output_table(statement)
            if output:
                result["output_table"] = output

        # extract input tables
        input_tables = _extract_input_tables(statement)
        result["input_tables"] = list(set(input_tables))

        # extract column mappings
        mappings = _extract_column_mappings(statement)
        result["column_mappings"] = mappings

    return result


def _extract_output_table(statement) -> str | None:
    if isinstance(statement, exp.Create):
        table = statement.find(exp.Table)
        if table:
            return table.name
    if isinstance(statement, exp.Insert):
        table = statement.find(exp.Table)
        if table:
            return table.name
    return None


def _extract_input_tables(statement) -> list[str]:
    tables = []

    # collect all CTEs so we can exclude them from input tables
    cte_names = set()
    for cte in statement.find_all(exp.CTE):
        if cte.alias:
            cte_names.add(cte.alias.lower())

    output_table = None
    if isinstance(statement, (exp.Create, exp.Insert)):
        t = statement.find(exp.Table)
        if t:
            output_table = t.name.lower()

    for table in statement.find_all(exp.Table):
        name = table.name.lower()
        if name and name not in cte_names and name != output_table:
            tables.append(name)

    return tables


def _extract_column_mappings(statement) -> list[dict]:
    mappings = []

    # find the SELECT inside CREATE TABLE AS SELECT or INSERT INTO SELECT
    select = statement.find(exp.Select)
    if not select:
        return mappings

    for expr in select.expressions:
        target_col = _get_alias_or_name(expr)
        source_cols = _get_source_columns(expr)

        if target_col:
            mappings.append({
                "target_column": target_col,
                "source_columns": source_cols
            })

    return mappings


def _get_alias_or_name(expr) -> str | None:
    if isinstance(expr, exp.Alias):
        return expr.alias.lower()
    if isinstance(expr, exp.Column):
        return expr.name.lower()
    return None


def _get_source_columns(expr) -> list[str]:
    cols = []
    for col in expr.find_all(exp.Column):
        cols.append(col.name.lower())
    return list(set(cols))


def parse_all_sql_files(folder: str) -> list[dict]:
    results = []
    for fname in sorted(os.listdir(folder)):
        if fname.endswith(".sql"):
            fpath = os.path.join(folder, fname)
            parsed = parse_sql_file(fpath)
            results.append(parsed)
    return results
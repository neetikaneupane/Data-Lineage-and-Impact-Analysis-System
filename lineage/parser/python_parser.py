import ast
import os


READ_CALLS  = {"read_csv", "read_parquet", "read_excel", "read_json"}
WRITE_CALLS = {"to_csv", "to_parquet", "to_excel", "to_json"}


def parse_python_file(filepath: str) -> dict:
    with open(filepath, "r") as f:
        source = f.read()

    filename = os.path.basename(filepath)
    tree = ast.parse(source)

    result = {
        "file": filename,
        "inputs":  [],
        "outputs": []
    }

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        func = node.func

        # pd.read_csv("path") style
        if isinstance(func, ast.Attribute):
            if func.attr in READ_CALLS:
                path = _extract_first_string_arg(node)
                if path:
                    result["inputs"].append(path)

            if func.attr in WRITE_CALLS:
                path = _extract_first_string_arg(node)
                if path:
                    result["outputs"].append(path)

    return result


def _extract_first_string_arg(node: ast.Call) -> str | None:
    if node.args and isinstance(node.args[0], ast.Constant):
        return node.args[0].value
    for kw in node.keywords:
        if kw.arg == "path" and isinstance(kw.value, ast.Constant):
            return kw.value.value
    return None


def parse_all_python_files(folder: str) -> list[dict]:
    results = []
    for fname in sorted(os.listdir(folder)):
        if fname.endswith(".py"):
            fpath = os.path.join(folder, fname)
            parsed = parse_python_file(fpath)
            results.append(parsed)
    return results
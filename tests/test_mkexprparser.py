
import glob
import os.path
import pytest

from gscons import mkexpr

def get_mkexprparser_expr_files():
    mkfiles = glob.glob('test*.expr',
                        root_dir=os.path.join(os.path.dirname(__file__), 'mkexprparser_testdata'))
    return sorted(mkfiles)

@pytest.mark.parametrize("expr_file", get_mkexprparser_expr_files())
def test_mkexprparser(expr_file):
    parser = mkexpr.initialize()

    expr_file_path=os.path.join(os.path.dirname(__file__), 'mkexprparser_testdata', expr_file)

    parsed_expr = parser.parse_file(expr_file_path)

    print(f"parsed_expr={str(parsed_expr)}")
    if len(parsed_expr) > 1:
        for i in range(0, min(len(parsed_expr), 2)):
            print(parsed_expr[i].to_str())

    assert len(parsed_expr) == 1
    result = parser.call_actions(parsed_expr[0])
    print(f"{result.debug_struct()}")

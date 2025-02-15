
import glob
import os.path
import pytest

from gscons import mkparser

def get_mkparser_mk_files():
    mk_files = glob.glob('test*.mk',
                        root_dir=os.path.join(os.path.dirname(__file__), 'mkparser_testdata'))
    return sorted(mk_files)

@pytest.mark.parametrize("mk_file", get_mkparser_mk_files())
def test_mkparser(mk_file):
    parser = mkparser.initialize()

    mk_file_path=os.path.join(os.path.dirname(__file__), 'mkparser_testdata', mk_file)

    parsed_mk = parser.parse_file(mk_file_path)

    print(f"{parsed_mk}")
    #for i in range(0, min(len(parsed_mk), 3)):
    #    print(parsed_mk[i].to_str())

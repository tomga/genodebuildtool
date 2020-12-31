
import os
import sys

buildtool_file_path = os.path.abspath(__file__)
BUILDTOOL_PATH=os.path.dirname(buildtool_file_path)
sys.path.insert(0, BUILDTOOL_PATH)

from gbuildtool import buildtool

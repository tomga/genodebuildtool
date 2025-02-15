
SCRIPTS_DIR=../genodebuildtool/test/mkparser/testdata

F00=$(shell realpath $(SCRIPTS_DIR))
F01=$(wildcard $(F00)/*)
F02=$(basename $(F01))

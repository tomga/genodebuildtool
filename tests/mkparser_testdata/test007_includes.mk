
SCRIPTS_DIR=../genodebuildtool/test/mkparser/testdata

include $(SCRIPTS_DIR)/test002_simple_assign.mk

TEST_FILE=test004_combined.mk

include $(SCRIPTS_DIR)/$(TEST_FILE)

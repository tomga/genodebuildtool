
TESTDIR=/abc/def

vpath test.cc /abc
vpath %.cc    $(TESTDIR)/src

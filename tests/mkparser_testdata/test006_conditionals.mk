

ABC=XYZ
BCD=xyz
CDE:=BC
DEF:=abc

ifdef ABC
RES00=res00
endif

ifdef CDE
RES01=res01
else
RES02=res02
endif

ifdef A$(CDE)
RES03=res03
endif

ifndef XYZ
RES04=res04
endif

ifndef CDE
RES05=res05
else
RES06=res06
endif

ifeq ($(A$(CDE)), XYZ)
RES07=res07
endif

ifneq (XYZ, XYZ)
RES08=res08
else
RES09=res09
endif

ifdef XYZ
RES10=res10
else ifneq (XYZ, XYZ)
RES11=res11
else
RES12=res12
endif



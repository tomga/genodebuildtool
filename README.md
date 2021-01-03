
# Build Tools for Genode

Set of tools for making development process of Genode better and
easier, where *better and easier* is defined completely by me and this
definition may not be consistent with the view of others.

### Currently considered list of goals are:

 * reimplement Genode build system with SCons to:
   * overcome some problems I feel are broken in curent Make based build system
   * deeply understand current build system
   * be able to programatically access all build commands and flags to build targets

 * integrate build system with some IDE possibly Eclipse with the goals to:
   * allow to see targets directly in IDE and build them
   * provide proper compilation flags needed for proper includes processing by IDE
   * provide source files used to build targets (tricky due to *specs*
     mechanism used in Genode build system)

 * integration with clang based tools for static analysis of code


### Current state

Currently it is a work in progress and it is in initial state. It is
published in case someone will be interested in this work.

Code is in subdirectories briefly described below.

## [gscons](gscons)

Reimplementation of Genode build system using SCons. Details and
current state in [README](gscons/README.md) in gscons directory.

## [gbuildtool](gbuildtool)

Tool for running builds of Genode (Make and SCons based) and gathering
information about those builds in database to allow verification of
correctness and completeness. More information about them in its
[README](gbuildtool/README.md).

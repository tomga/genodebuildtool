
# GScons

Package that allows to use SCons to build Genode. It uses information
about targets being built from existing makefiles (as much as
possible) and uses it to instruct SCons.

The goal for this work is to be one to one replacement with some
improvements that are gained by using SCons and some by better
controlling build rules by using Python to control build.

### Improvements

 * build only what is really needed to be rebuilt - avoid big
   recompilations e.g. after switching branches due to unclear reasons
   (this actually became less important after adding easy way to
   enable *ccache* in original build)

 * avoid repetitions in flags passed to compiler - include paths are
   sometimes repeated four times in original build (possibly it can be
   fixed in make based builds as well)

 * be able to log more informations about process of creating build
   commands and flags - due to use of python and more procedural
   handling of build definitions

 * get rid of absolute paths to files in repository - it disallows (I
   think) use of *ccache* for different compilation environments if
   they are not in exactly the same absolute path and I think that it
   is a step to have reproducible builds


### Possible regressions

 * possibly some build dependencies may be missed in case SCons can't
   handle them yet (I don't know about such cases but it is possible
   that due to the fact that it does not use compiler for tracing
   dependencies it can miss something in some corner cases)

 * possibly some builds can be slower (I did not measure it yet - I
   expect gains on typical work when changing source, compiling and
   testing)


## Implementation

Implementation consists of two parts.

First is an ability to parse and interpret *makefiles* in range wide
enough to be able to read and process most of the build rule files in
Genode.

Second is a reimplementation of general Genode build system rules in
Python.

Those two functinalities combined together allow to create build a
working replacement of make based build system.


## Installation

Currently development and testing is performed on Ubuntu
20.04. Installation requires python3 and a possibility to create
Python virtual environment in which two packages should be installed:
 * SCons
 * parglare - lexer and parser implementation in Python used to parse
   makfiles

Following commands should be enough:

    # install required Ubuntu packages
    sudo apt install python3 python3-virtualenv

    # create and activate virtual environment
    virtualenv -p python3 pygenode
    . pygenode/bin/activate

    # install required python packages
    pip install scons
    pip install parglare


## Preparing Genode repository

There are only two things required to do in Genode repository to
prepare them to support GScons builds. Two symbolic links to
*SConstruct* and *SConscript* files provided by *genodebuildtool* have
to be created.

Assuming that current directory is root of Genode checkout and
genodebuildtool is checked out aside of genode repository following
commands are needed:

    ln -s ../genodebuildtool/gscons/SConstruct
    ln -s ../genodebuildtool/gscons/SConscript


## Preparing build directory

Nothing more than creating normal Genode build system build directory
is really needed but it is good to do two things: remove link to
*build.mk* to effectively disable make based build in that directory
and create a dummy *SCons* indicator file to avoid GScons to work in
build directories that it is not supposed to.

In consequence creating a build directory for GScons build may look
like:

    tool/create_builddir x86_64 BUILD_DIR=build/linux_s
    touch build/linux_s/SCons
    rm build/linux_s/Makefile


## Usage

Generally using GScons to build Genode is much similar to make based
build. Main difference is that it is started from Genode root
directory and build directory must be provided as *BUILD*
parameter. Additionally *KERNEL* and *BOARD* are supported like in
make based build. Below there are sample commands that constitute easy
introduction:

Sample build of one program target:

    scons BUILD=build/linux_s BOARD=linux test/log

Similarly to make based build multiple targets are allowed:

    scons BUILD=build/linux_s BOARD=linux core init test/log

As an extension target patterns be provided with asterisks:

    scons BUILD=build/linux_s BOARD=linux 'test/*' 'drivers/*'

Sometimes it is important to exclude some targets:

    scons BUILD=build/linux_s BOARD=linux '*' PROG_EXCLUDES='kernel'

And similarly excludes can be provided as patterns

    scons BUILD=build/linux_s BOARD=linux '*' PROG_EXCLUDES='kernel test/*'

Similarly to program targets library targets can be provided:

    scons BUILD=build/linux_s BOARD=linux LIB='cxx'

And patterns and excludes are also supported:

    scons BUILD=build/linux_s BOARD=linux LIB='*' LIB_EXCLUDES='*png* net'

Normally build commands are not printed. They can be enabled with
*VERBOSE_OUTPUT* parameter:

    scons BUILD=build/linux_s BOARD=linux VERBOSE_OUTPUT=yes test/log

In addition to build commands there is additional output generated by
code that processes build information. By default log level for that
processing is set to *info*. It is possible to make this output more
verbose with:

    scons BUILD=build/linux_s BOARD=linux LOG_LEVEL=debug test/log

Or less verbose with by providing *notice*, *warning* or *error* value:

    scons BUILD=build/linux_s BOARD=linux LOG_LEVEL=warning test/log

Brief description of accepted parameters can be retrieved by executing:

    scons --help


## ccache support

SCons build variant implements support for *ccache* in the same way it
is implemented in original make based builds. Only *CCACHE* variable
with value *yes* in *build.conf* is needed.


## Current state

Currently build of everything that builds properly in make based build
in following repositories:

 * base-hw
 * base-linux
 * base
 * os
 * demo
 * dde_linux

Below there is a list of currently tested configurations and builds on
*master* and *staging* (architecture, kernel, board):

 * linux, linux, linux
 * x86_64, hw, pc
 * arm_v6, hw, rpi
 * arm_v7a, hw, pbxa9
 * arm_v8a, hw, rpi3

More about testing methodology in [gbuildtool](../gbuildtool).


## TODO

Here is a list of known things to do:

 * extend support for more repositories

 * improve integration with *run* tool - better handling of
   dependencies

 * support for depots
   * as build targets
   * as dependencies from run scripts

 * consider some support for make rules

 * refactoring:
   * split target type specific parts from *genode_sconscript.py* to
     proper files


## Some implementation details


### Overlays - handling of hard or special cases

Parsing of makefiles in general is not that easy (at least for me) and
my parser has some limitations and some simplifications. Additionally
during development I found some errors in existing makefiles that were
not found yet due to being ignored by make based build system.

I did not want to required any source changes in Genode repository to
perform GScons based build therefore I implemented overlays mechanism
that allow to provide replacement or modification to specific existing
makefiles which I name *overlays*.

There are different reasons for providing overlays:

 * generally build rules from makefiles are not interpreted at all -
   they need to be reimplemented (example for
   `repos/base/lib/mk/cxx.mk`)

 * makefiles can contain syntax that my make parser is not capable to
   process, e.g.:

    * some characters (especially braces and dollar) inside of
      expressions - for such cases it is possible to escape such
      characters (with double tilde) in an alternative version or with
      a patch (example provided for
      `repos/base-linux/lib/import/import-lx_hybrid.mk`)

 * errors in existing makefiles (example for
   `repos/base-linux/src/test/lx_hybrid_errno/target.mk`)

There are different types of overlays:

 * overlays with `.sc` extension are overlays implemented in Python

 * overlays with `.mk` extension are alternative versions of original
   makefiles

 * overlays with `.patch` extension contain a patch that has to be
   applied to original makefile


GScons attempts to support different versions of Genode in parallel so
there is a possibility that file for which overlay was created will
change over time. That is why overlays are created for specific file
versions. To create overlay the `.ovr` file has to be created that
contains mapping from md5 sum of original file for which overlay is
created to name of the actual overlay file. It is possible to have one
overlay for different original files (example overlay for
`repos/base/lib/mk/cxx.mk`).

Existing overlays are stored in [genode](../genode) subdirectory of
this repository and by default are looked for in that location.

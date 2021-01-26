
# Build tool

This package contains a tool that is used mostly to verify correctness
of GScons builds with relation to make based builds.

It allows to run make and GSCons builds with flags allowing for
extraction of build commands. Then it parses build logs and stores in
local sqlite database commands used to build targets along with their
*canonicalized* versions (canonicalization means standardizing
arguments order and form) to be able to compare them in different
builds.


## Installation

The same Python virtual environment as for GScons build is required.


## Usage

Flags accepted by buildtool can be retrieved using:

    python ../genodebuildtool/buildtool/buildtool.py --help

Following builds are tested to pass properly and provide identical
results:

    tool/create_builddir linux BUILD_DIR=build/linux_s; touch build/linux_s/SCons; rm build/linux_s/Makefile
    tool/create_builddir linux BUILD_DIR=build/linux_m # makefile based build
    python ../genodebuildtool/buildtool/buildtool.py --check-builds --board linux -b linux_m -b linux_s -p '*' -np app/status_bar drivers/audio drivers/framebuffer/sdl drivers/usb_block test/lx_hybrid_ctors test/sanitizer test/xml_generator

    tool/create_builddir arm_v6 BUILD_DIR=build/arm6_s; touch build/arm6_s/SCons; rm build/arm6_s/Makefile
    tool/create_builddir arm_v6 BUILD_DIR=build/arm6_m # makefile based build
    python ../genodebuildtool/buildtool/buildtool.py --check-builds --board rpi -b arm6_m -b arm6_s -p '*' -np bbl kernel test/sanitizer test/xml_generator

    tool/create_builddir arm_v7a BUILD_DIR=build/arm7_s; touch build/arm7_s/SCons; rm build/arm7_s/Makefile
    tool/create_builddir arm_v7a BUILD_DIR=build/arm7_m # makefile based build
    python ../genodebuildtool/buildtool/buildtool.py --check-builds --kernel hw --board pbxa9 -b arm7_m -b arm7_s -p '*' -np bbl bootstrap/hw kernel test/sanitizer test/xml_generator

    tool/create_builddir arm_v8a BUILD_DIR=build/arm8_s; touch build/arm8_s/SCons; rm build/arm8_s/Makefile
    tool/create_builddir arm_v8a BUILD_DIR=build/arm8_m # makefile based build
    python ../genodebuildtool/buildtool/buildtool.py --check-builds --kernel hw --board rpi3 -b arm8_m -b arm8_s -p '*' -np bbl bootstrap/hw kernel test/sanitizer test/xml_generator


## TODO

Here is a list of things planned to do in short term:

 * support options for creating build directories and enable
   repositories (option placeholders already exist but are not
   implemented)

 * make more options to access compilation database from *buildtool*

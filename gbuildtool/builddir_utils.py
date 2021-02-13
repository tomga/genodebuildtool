
import os
import pathlib

from gbuildtool import buildtool_utils


def recreate_mk_builddir(build_dir, arch):
    recreate_generic_builddir(build_dir, arch)


def recreate_sc_builddir(build_dir, arch):
    recreate_generic_builddir(build_dir, arch)

    mkfile = os.path.join(build_dir, 'Makefile')
    os.remove(mkfile)

    scfile = os.path.join(build_dir, 'SCons')
    pathlib.Path(scfile).touch()


def recreate_generic_builddir(build_dir, arch):

    precious_files = [ 'etc/build.conf',
                       'etc/specs.conf']

    # read precious files
    precious_files_content = {}
    for pfile_name in precious_files:
        pfile_fullname = os.path.join(build_dir, pfile_name)
        with open(pfile_fullname, 'rb') as pfile:
            precious_files_content[pfile_name] = pfile.read()

    assert build_dir.startswith('build/'), "sanity check before executing rm -rf"

    command = 'rm -rf %s' % build_dir
    descr = 'Removing old build directory'
    buildtool_utils.asserted_command_execute(descr, command)

    command = 'tool/create_builddir %s BUILD_DIR=%s' % (arch, build_dir)
    descr = 'Creating new build directory'
    buildtool_utils.asserted_command_execute(descr, command)

    # restore precious files
    for pfile_name in precious_files:
        pfile_fullname = os.path.join(build_dir, pfile_name)
        os.remove(pfile_fullname)
        with open(pfile_fullname, 'wb') as pfile:
            pfile.write(precious_files_content[pfile_name])

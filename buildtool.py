
import argparse
import datetime
import os
import parglare
import pprint
import sqlite3
import subprocess
import sys

import buildinfo_storer
import db_utils
import schema
import mkevaluator
import mkparser
import mklogparser
import sclogparser

import buildtool_utils

import genode_util_mk_functions
genode_util_mk_functions.register_mk_functions(mkevaluator.functionsDict)



def arguments_parse():
    """Parse buildtool options.
    """

    argparser = argparse.ArgumentParser('buildtool')
    argparser.add_argument('-b', '--build', action='append',
                           help='build directory')
    argparser.add_argument('-l', '--lib', nargs='+', default=[],
                           help='target libraries')
    argparser.add_argument('-nl', '--no-lib', nargs='+', default=[],
                           help='disabled target libraries')
    argparser.add_argument('-p', '--prog', nargs='+', default=[],
                           help='target executables')
    argparser.add_argument('-np', '--no-prog', nargs='+', default=[],
                           help='disabled target executables')
    argparser.add_argument('-r', '--run', nargs='+', default=[],
                           help='target run scripts')
    argparser.add_argument('--kernel',
                           help='target run kernel')
    argparser.add_argument('--board',
                           help='target run kernel')
    argparser.add_argument('--database', default='build/buildtool.db',
                           help='database location')
    argparser.add_argument('--logs', default='../logs',
                           help='target run kernel')
    argparser.add_argument('--log-level', default='none',
                           choices=['none', 'error', 'warning', 'notice', 'info', 'debug'],
                           help='scons helper code diagnostics log level')

    argparser.add_argument('--db-reset-data', action='store_true')

    argparser.add_argument('--builddir-recreate', action='store_true')
    argparser.add_argument('--builddir-enable-repos', nargs='+', default=[])

    argparser.add_argument('--check-builds', action='store_true')

    argparser.add_argument('--log', nargs='+', default=[],
                           help='log files to process')
    argparser.add_argument('--test-database', action="store_true")
    argparser.add_argument('--test-mkparser', action="store_true")
    argparser.add_argument('--test-mklogparser', action="store_true")
    argparser.add_argument('--test-sclogparser', action="store_true")
    argparser.add_argument('--test-mkdbstore', action="store_true")
    argparser.add_argument('--test-scdbstore', action="store_true")

    return argparser.parse_args()


def arguments_print(opts):
    print("Arguments")
    for opt in vars(opts):
        print("   %s: %s" % (str(opt), str(getattr(opts, opt))))



def database_connect(opts):
    """Returns verified connnection to build database.
    """

    db_file = opts.database
    if (opts.test_database or
        opts.test_mklogparser or opts.test_sclogparser or
        opts.test_mkdbstore or opts.test_scdbstore):
        db_file = os.path.join(os.path.dirname(opts.database), 'testdb.db')
        print('Using test database: %s' % (db_file))

    build_db = sqlite3.connect(db_file)

    check_result = schema.db_check_schema(build_db, schema.CURRENT_SCHEMA_VERSION)
    print('Check schema result: %s' % ('OK' if check_result else 'EMPTY'))
    
    if not check_result:
        print("Preparing schema")
        schema.db_prepare_schema(build_db, schema.CURRENT_SCHEMA_VERSION)

        check_result = schema.db_check_schema(build_db, schema.CURRENT_SCHEMA_VERSION)
        print('Check schema result: %s' % ('OK' if check_result else 'EMPTY'))

    return build_db



def get_build_arch(build_name):
    build_dir = 'build/%s' % (build_name)
    specs_conf_file = '%s/etc/specs.conf' % (build_dir)

    parser = mkparser.initialize()
    mkcache = mkevaluator.MkCache(parser)
    specs_conf = mkcache.get_parsed_mk(specs_conf_file)
    env = mkevaluator.MkEnv(mkcache)
    specs_conf.process(env)

    arch = env.var_values('SPECS')[0]

    return arch


def is_mk_build(build_name):
    build_dir = 'build/%s' % (build_name)
    mk_file = '%s/Makefile' % (build_dir)
    return (os.path.isdir(build_dir)
            and os.path.exists(mk_file)
            and not os.path.isdir(mk_file))


def is_sc_build(build_name):
    build_dir = 'build/%s' % (build_name)
    sc_file = '%s/SCons' % (build_dir)
    return (os.path.isdir(build_dir)
            and os.path.exists(sc_file)
            and not os.path.isdir(sc_file))



def parse_mk_log(log_file):
    logparser = mklogparser.initialize()
    logparse_result = logparser.parse_file(log_file)
    #buildtool_utils.Python2PrettyPrinter().pprint(logparse_result.debug_struct())
    return logparse_result



def parse_sc_log(log_file):
    logparser = sclogparser.initialize()
    logparse_result = logparser.parse_file(log_file)
    #buildtool_utils.Python2PrettyPrinter().pprint(logparse_result.debug_struct())
    return logparse_result



def targets_require_expanding(opts):
    for tested_list in [opts.lib, opts.no_lib, opts.prog, opts.no_prog]:
        patterns = [ pattern for pattern in tested_list if '*' in pattern ]
        if len(patterns) > 0:
            return True
    return False


def do_sc_expand_targets(build, opts):

    stamp_dt = datetime.datetime.now()
    tstamp = f"{stamp_dt:%Y%m%d_%H%M%S}"
    arch = get_build_arch(build)

    log_file = '%s/%s_%s_%s_%s.TARGETS' % (opts.logs,
                                           tstamp,
                                           arch,
                                           opts.kernel if opts.kernel is not None else '',
                                           opts.board if opts.board is not None else '')

    kernel = 'KERNEL=%s' % (opts.kernel) if opts.kernel is not None else ''
    board = 'BOARD=%s' % (opts.board) if opts.board is not None else ''

    command = ' '.join([p for p in ['scons',
                                    'DEV_ONLY_EXPAND_TARGETS=yes',
                                    'BUILD=build/%s' % (build),
                                    '%s' % (kernel),
                                    '%s' % (board),
                                    "LIB='%s'" % ' '.join(opts.lib) if len(opts.lib) > 0 else '',
                                    '%s' % ' '.join(["'%s'" % (prog) for prog in opts.prog]),
                                    "LIB_EXCLUDES='%s'" % ' '.join(opts.no_lib) if len(opts.no_lib) > 0 else '',
                                    "PROG_EXCLUDES='%s'" % ' '.join(opts.no_prog) if len(opts.no_prog) > 0 else '',
                                    '2>&1 | tee %s' % (log_file)] if p != ''])
    print('Expanding targets: %s' % command)
    exit_code, output = buildtool_utils.command_execute(command)

    if exit_code != 0:
        print("ERROR: expanding targets process failed")
        quit()

    target_libs = None
    target_progs = None
    with open(log_file, 'r') as log:
        for line in log:
            if line.startswith('LIBS: '):
                target_libs = line[len('LIBS: '):].strip().split()
            if line.startswith('PROGS: '):
                target_progs = line[len('PROGS: '):].strip().split()

    if target_libs is None or target_progs is None:
        print("ERROR: expanding targets process did not produce expected LIBS: and PROGS:")
        quit()

    opts.lib = target_libs
    opts.no_lib = []
    opts.prog = target_progs
    opts.no_prog = []


def do_expand_targets(opts):

    if not targets_require_expanding(opts):
        return

    arch = None
    for build in opts.build:
        current_arch = get_build_arch(build)
        if arch is not None and arch != current_arch:
            print("ERROR: targets with asterisks allowed only for builds with consistent archiecture")
            print("       but detected at least two: %s and %s" % (arch, current_arch))
            quit()
        arch = current_arch

    targets_expanded = False
    for build in opts.build:
        if is_sc_build(build):
            targets_expanded = True
            do_sc_expand_targets(build, opts)
            break

    if not targets_expanded:
        print("ERROR: targets with asterisks provided and no scons build available")
        quit()

    #arguments_print(opts)


def do_mk_build(build_name, opts, stamp_dt, log_file):

    if len(opts.lib) > 1:
        print("ERROR: only single library allowed with make build but asked for '%s'" % (str(opts.lib)))
        quit()

    kernel = 'KERNEL=%s' % (opts.kernel) if opts.kernel is not None else ''
    board = 'BOARD=%s' % (opts.board) if opts.board is not None else ''

    command = ' '.join([p for p in ['LANG=C',
                                    'make VERBOSE= VERBOSE_MK= VERBOSE_DIR=',
                                    '-C build/%s' % (build_name),
                                    '%s' % (kernel),
                                    '%s' % (board),
                                    'LIB=%s' % opts.lib[0] if len(opts.lib) > 0 else '',
                                    '%s' % ' '.join(opts.prog),
                                    '%s' % ' '.join(opts.run),
                                    '2>&1 | tee %s' % (log_file)] if p != ''])
    print('Executing: %s' % command)
    exit_code, output = buildtool_utils.command_execute(command)

    return exit_code

    
def do_sc_build(build_name, opts, stamp_dt, log_file):

    kernel = 'KERNEL=%s' % (opts.kernel) if opts.kernel is not None else ''
    board = 'BOARD=%s' % (opts.board) if opts.board is not None else ''

    command = ' '.join([p for p in ['scons',
                                    'BUILD=build/%s' % (build_name),
                                    'VERBOSE_OUTPUT=yes',
                                    'LOG_LEVEL=%s' % (opts.log_level) if opts.log_level != 'none' else '',
                                    '%s' % (kernel),
                                    '%s' % (board),
                                    "LIB='%s'" % ' '.join(opts.lib) if len(opts.lib) > 0 else '',
                                    '%s' % ' '.join(opts.prog),
                                    '2>&1 | tee %s' % (log_file)] if p != ''])
    print('Executing: %s' % command)
    exit_code, output = buildtool_utils.command_execute(command)

    return exit_code

    

def do_builds(opts, build_db):

    # check logs directory
    if not os.path.isdir(opts.logs):
        print("ERROR: logs directory '%s' does not exist" % (opts.logs))
        quit()

    stamp_dt = datetime.datetime.now()
    tstamp = f"{stamp_dt:%Y%m%d_%H%M%S}"

    build_exit_codes = {}

    for build in opts.build:

        if opts.db_reset_data:
            print('Clearing build db: %s' % (build))
            db_utils.clear_build_info(build_db, build)

        arch = get_build_arch(build)
        abs_dir = os.getcwd()
        rel_dir = 'build/%s' % (build)

        log_file = '%s/%s_%s_%s_%s.%s' % (opts.logs,
                                          tstamp,
                                          arch,
                                          opts.kernel if opts.kernel is not None else '',
                                          opts.board if opts.board is not None else '',
                                          build)

        if is_mk_build(build):
            print('Make type build: %s' % (build))
            exit_code = do_mk_build(build, opts, stamp_dt, log_file)
            run_time = None
            build_info = parse_mk_log(log_file)
            buildinfo_storer.store_build_info(build_db, build_info, build, 'make',
                                              stamp_dt, arch, log_file, run_time,
                                              abs_dir, rel_dir)
        elif is_sc_build(build):
            print('SCons type build: %s' % (build))
            exit_code = do_sc_build(build, opts, stamp_dt, log_file)
            run_time = None
            build_info = parse_sc_log(log_file)
            build_info.run_dir = abs_dir # this information is not in scons log
            buildinfo_storer.store_build_info(build_db, build_info, build, 'scons',
                                              stamp_dt, arch, log_file, run_time,
                                              abs_dir, rel_dir)
        else:
            print('Unknown build type: %s' % (build))

        build_exit_codes[build] = exit_code

    if opts.check_builds:
        if len(opts.build) != 2:
            print('ERROR: cannot compare %s builds' % (str(len(opts.build))))
        else:
            build0_name = opts.build[0]
            build1_name = opts.build[1]
            build0_ok = (build_exit_codes[build0_name] == 0)
            build1_ok = (build_exit_codes[build1_name] == 0)
            if build0_ok != build1_ok:
                print('ERROR: build results differ: %s %s and %s %s'
                      % (build0_name, 'SUCCEDED' if build0_ok else 'FAILED',
                         build1_name, 'SUCCEDED' if build1_ok else 'FAILED'))

            db_utils.compare_builds(build_db, build0_name, build1_name)


###
# parse configuration
###
def test_mkparser():
    parser = mkparser.initialize()
    mkcache = mkevaluator.MkCache(parser)

    # test.mk
    test_mk = mkcache.get_parsed_mk('/projects/genode/tmp/test.mk')
    pprint.pprint(test_mk.debug_struct(), width=180)

    env = mkevaluator.MkEnv(mkcache)
    test_mk.process(env)
    pprint.pprint(env.debug_struct('pretty'), width=200)
    quit()

    # build.conf
    build_conf = mkcache.get_parsed_mk('/projects/genode/genode/nbuild/linux/etc/build.conf')

    # specs.conf
    specs_conf = mkcache.get_parsed_mk('/projects/genode/genode/nbuild/linux/etc/specs.conf')

    #base_hw_specs_conf = mkcache.get_parsed_mk('/projects/genode/genode/repos/base-hw/etc/specs.conf')
    #pprint.pprint(base_hw_specs_conf.debug_struct(), width=180)

    # global.mk
    base_global = mkcache.get_parsed_mk('/projects/genode/genode/repos/base/mk/global.mk')
    #pprint.pprint(base_global.debug_struct(), width=180)


    # cxx.mk
    libcxx = mkcache.get_parsed_mk('/projects/genode/genode/repos/base/lib/mk/cxx.mk')
    pprint.pprint(libcxx.debug_struct(), width=180)


    # evaluate
    env = mkevaluator.MkEnv(mkcache)

    # initial variables
    env.get_create_var('BUILD_BASE_DIR').set_value(mkevaluator.MkRValueExpr.from_values_list(['/projects/genode/genode/nbuild/linux']))

    # process mk files
    build_conf.process(env)
    #pprint.pprint(env.debug_struct('pretty'), width=200)

    specs_conf.process(env)
    #pprint.pprint(env.debug_struct('pretty'), width=200)

    #base_hw_specs_conf.process(env)
    #pprint.pprint(env.debug_struct('pretty'), width=200)

    base_global.process(env)
    #pprint.pprint(env.debug_struct('pretty'), width=200)

    # overrides
    env.get_create_var('CC_OPT_DEP').set_value(mkevaluator.MkRValueExpr.from_values_list([]))
    env['fn_debug'](pprint.pformat(env.debug_struct('pretty'), width=200))


    # build.mk
    build_mk = mkcache.get_parsed_mk('/projects/genode/genode/tool/builddir/build.mk')


###
# Buildtool
###

opts = arguments_parse()
arguments_print(opts)

build_db = database_connect(opts)

if opts.test_database:
    database_connect(opts)
    quit()

if opts.test_mkparser:
    test_mkparser()
    quit()

if opts.test_mklogparser:
    for log_file in opts.log:
        parse_mk_log(log_file)
    quit()

if opts.test_sclogparser:
    for log_file in opts.log:
        parse_sc_log(log_file)
    quit()

if opts.test_mkdbstore:
    build = opts.build[0]
    stamp_dt = datetime.datetime.now()
    abs_dir = os.getcwd()
    rel_dir = 'build/%s' % (build)
    for log_file in opts.log:
        build_info = parse_mk_log(log_file)
        buildinfo_storer.store_build_info(build_db, build_info, build, 'make',
                                          stamp_dt, 'test', log_file, None,
                                          abs_dir, rel_dir)
    quit()

if opts.test_scdbstore:
    build = opts.build[0]
    stamp_dt = datetime.datetime.now()
    abs_dir = os.getcwd()
    rel_dir = 'build/%s' % (build)
    for log_file in opts.log:
        build_info = parse_sc_log(log_file)
        buildinfo_storer.store_build_info(build_db, build_info, build, 'make',
                                          stamp_dt, 'test', log_file, None,
                                          abs_dir, rel_dir)
    quit()


do_expand_targets(opts)
do_builds(opts, build_db)

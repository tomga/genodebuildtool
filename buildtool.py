
import argparse
import datetime
import os
import parglare
import pprint
import sqlite3
import subprocess
import sys

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
    argparser.add_argument('-p', '--prog', nargs='+', default=[],
                           help='target executables')
    argparser.add_argument('-r', '--run', nargs='+', default=[],
                           help='target run scripts')
    argparser.add_argument('--kernel',
                           help='target run kernel')
    argparser.add_argument('--board',
                           help='target run kernel')
    argparser.add_argument('--database', default='buildtool.db',
                           help='database location')
    argparser.add_argument('--logs', default='../logs',
                           help='target run kernel')

    argparser.add_argument('--test-mklogparser', nargs='+')
    argparser.add_argument('--test-sclogparser', nargs='+')

    return argparser.parse_args()


def arguments_print(opts):
    print("Arguments")
    for opt in vars(opts):
        print("   %s: %s" % (str(opt), str(getattr(opts, opt))))



def database_connect(opts):
    """Returns verified connnection to build database.
    """

    build_db = sqlite3.connect(opts.database)

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
    buildtool_utils.Python2PrettyPrinter().pprint(logparse_result.debug_struct())



def parse_sc_log(log_file):
    logparser = sclogparser.initialize()
    logparse_result = logparser.parse_file(log_file)
    buildtool_utils.Python2PrettyPrinter().pprint(logparse_result.debug_struct())




def do_mk_build(build_name, opts, stamp_dt, log_file):

    if len(opts.lib) > 1:
        print("ERROR: only single library allowed with make build but asked for '%s'" % (str(opts.lib)))
        quit()

    kernel = 'KERNEL=%s' % (opts.kernel) if opts.kernel is not None else ''
    board = 'BOARD=%s' % (opts.board) if opts.board is not None else ''

    command = ' '.join(['LANG=C',
                        'make VERBOSE= VERBOSE_MK= VERBOSE_DIR=',
                        '-C build/%s' % (build_name),
                        '%s' % (kernel),
                        '%s' % (board),
                        'LIB=%s' % opts.lib[0] if len(opts.lib) > 0 else '',
                        '2>&1 | tee %s' % (log_file)])
    output = buildtool_utils.command_execute(command)


    
def do_sc_build(build_name, opts, stamp_dt, log_file):

    if len(opts.lib) > 1:
        print("ERROR: only single library allowed with make build but asked for '%s'" % (str(opts.lib)))
        quit()

    kernel = 'KERNEL=%s' % (opts.kernel) if opts.kernel is not None else ''
    board = 'BOARD=%s' % (opts.board) if opts.board is not None else ''

    command = ' '.join(['scons',
                        'BUILD=build/%s' % (build_name),
                        'VERBOSE_OUTPUT=yes',
                        '%s' % (kernel),
                        '%s' % (board),
                        'LIB=%s' % opts.lib[0] if len(opts.lib) > 0 else '',
                        '2>&1 | tee %s' % (log_file)])
    output = buildtool_utils.command_execute(command)


    

def do_builds(opts):

    # check logs directory
    if not os.path.isdir(opts.logs):
        print("ERROR: logs directory '%s' does not exist" % (opts.logs))
        quit()

    stamp_dt = datetime.datetime.now()
    tstamp = f"{stamp_dt:%Y%m%d_%H%M%S}"

    for build in opts.build:

        arch = get_build_arch(build)

        log_file = '%s/%s_%s_%s_%s.%s' % (opts.logs,
                                          tstamp,
                                          arch,
                                          opts.kernel if opts.kernel is not None else '',
                                          opts.board if opts.board is not None else '',
                                          build)

        if is_mk_build(build):
            print('Make type build: %s' % (build))
            do_mk_build(build, opts, stamp_dt, log_file)
            parse_mk_log(log_file)
        elif is_sc_build(build):
            print('SCons type build: %s' % (build))
            do_sc_build(build, opts, stamp_dt, log_file)
            parse_sc_log(log_file)
        else:
            print('Unknown build type: %s' % (build))



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
    pprint.pprint(env.debug_struct('pretty'), width=200)


    # build.mk
    build_mk = mkcache.get_parsed_mk('/projects/genode/genode/tool/builddir/build.mk')


###
# Buildtool
###

opts = arguments_parse()
arguments_print(opts)

if opts.test_mklogparser is not None:
    for log_file in opts.test_mklogparser:
        parse_mk_log(log_file)
    quit()

if opts.test_sclogparser is not None:
    for log_file in opts.test_sclogparser:
        parse_sc_log(log_file)
    quit()


build_db = database_connect(opts)
do_builds(opts)

try:
    #test_mkparser()
    pass
except parglare.ParseError as parseError:
    print(str(parseError))
    print(str(parseError.symbols_before))
    print(str(parseError.symbols_before[0]))




import glob
import subprocess

# debug support
import pprint

# buildtoool packages
import mkevaluator
import mkparser
import mklogparser

import genode_tools as tools


import genode_util_mk_functions
genode_util_mk_functions.register_mk_functions(mkevaluator.functionsDict)


def sconscript(env):

    build_dir = env['BUILD']
    process_builddir(build_dir, env)


parser = mkparser.initialize()
mkcache = mkevaluator.MkCache(parser)


def process_builddir(build_dir, env):
    """Process build targets for given build directory.

    Mimics behavior of tool/builddir/build.mk
    """


    build_env = mkevaluator.MkEnv(mkcache)


    ### handle build.conf
    build_conf = mkcache.get_parsed_mk('%s/etc/build.conf' % (build_dir))
    build_conf.process(build_env)
    #pprint.pprint(build_env.debug_struct('pretty'), width=200)


    build_env.var_set('BUILD_BASE_DIR', '%s' % (build_dir))
    build_env.var_set('DEBUG_DIR', '%s/debug' % (build_dir))
    build_env.var_set('INSTALL_DIR', '%s/bin' % (build_dir))
    build_env.var_set('LIB_CACHE_DIR', '%s/var/libcache' % (build_dir))


    repositories = build_env.var_values('REPOSITORIES')
    env['REPOSITORIES'] = repositories

    base_dir = build_env.var_value('BASE_DIR')
    env['BASE_DIR'] = base_dir

    ### handle */etc/specs.conf files
    repositories_specs_conf_files = tools.find_files('%s/etc/specs.conf', repositories)
    specs_conf_files = repositories_specs_conf_files + ['%s/etc/specs.conf' % (build_dir)]
    print("processing specs files: %s" % (str(specs_conf_files)))
    for specs_conf_file in specs_conf_files:
        specs_conf = mkcache.get_parsed_mk(specs_conf_file)
        specs_conf.process(build_env)
    #pprint.pprint(build_env.debug_struct('pretty'), width=200)


    ### handle mk/spec/$(SPEC).mk files
    #
    # NOTE: it is suspicious that only first found mk/spec/$(SPEC).mk
    #       file is included - there is no easily visible rule to know
    #       which is selected but currently just mimic behaviour from
    #       build.mk
    specs = build_env.var_values('SPECS')
    print("SPECS: %s" % (specs))
    specs_mk_files = []
    for spec in specs:
        specs_mk_file = tools.find_first(repositories, 'mk/spec/%s.mk' % (spec))
        if specs_mk_file is not None:
            specs_mk_files += [specs_mk_file]

    base_specs_mk_files = tools.find_files(base_dir + '/mk/spec/%s.mk', specs)
    specs_mk_files = list(set(specs_mk_files + base_specs_mk_files))

    print("processing <spec>.mk files: %s" % (str(specs_mk_files)))
    for specs_mk_file in specs_mk_files:
        specs_mk = mkcache.get_parsed_mk(specs_mk_file)
        specs_mk.process(build_env)
    #pprint.pprint(build_env.debug_struct('pretty'), width=200)


    ### handle global.mk
    base_global_mk = mkcache.get_parsed_mk('%s/mk/global.mk' % (base_dir))
    base_global_mk.process(build_env)
    #pprint.pprint(build_env.debug_struct('pretty'), width=200)


    ### handle LIBGCC_INC_DIR
    #
    # NOTE: probably it should be moved before processing global.mk as
    #       it is appended there to ALL_INC_DIR; in recursive make
    #       case it gets included there later
    temp_mk = parser.parse("""
export LIBGCC_INC_DIR = $(shell dirname `$(CUSTOM_CXX_LIB) -print-libgcc-file-name`)/include
    """)
    temp_mk.process(build_env)
    #build_env.var_set('LIBGCC_INC_DIR',
    #                  '/usr/local/genode/tool/19.05/bin/../lib/gcc/x86_64-pc-elf/8.3.0/include')
    pprint.pprint(build_env.debug_struct('pretty'), width=200)



    process_lib('cxx', env, build_env)
    #process_lib('ld', env, build_env)


def process_lib(lib_name, env, build_env):
    """Process library build rules.

    Build rules are read from <lib>.mk file like in standard Genode
    build (repos/<repo>/lib/mk/<lib>.mk) but there are possibilities
    to overwrite default with providing build rules in
    <buildtool>/genode/repos/<repo>/lib/mk/<lib>.py file where <repo>
    must be the same as for found <lib>.mk file.
    """

    #import rpdb2
    #rpdb2.start_embedded_debugger('password')

    ### TODO calculate SYMBOLS
    # first required for ld
    # LIB_MK_DIRS  = $(foreach REP,$(REPOSITORIES),$(addprefix $(REP)/lib/mk/spec/,     $(SPECS)) $(REP)/lib/mk)
    # SYMBOLS_DIRS = $(foreach REP,$(REPOSITORIES),$(addprefix $(REP)/lib/symbols/spec/,$(SPECS)) $(REP)/lib/symbols)


    ### handle base-libs.mk
    base_libs_mk_file = '%s/mk/base-libs.mk' % (env['BASE_DIR'])
    base_libs_mk = mkcache.get_parsed_mk(base_libs_mk_file)
    base_libs_mk.process(build_env)


    ### skipping util.inc as it is implemented in python


    ### skipping $(SPEC_FILES) as they are already included
    #
    # NOTE: passing this option is not documented


    ### handle include <lib>.mk
    build_env.var_set('called_from_lib_mk', 'yes')

    lib_mk_file = tools.find_first(env['REPOSITORIES'], 'lib/mk/%s.mk' % (lib_name))
    if lib_mk_file is None:
        print("Build rules file not found for library '%s'" % (lib_name))
        quit()

    print("Parsing build rules for library '%s' from '%s'" % (lib_name, lib_mk_file))
    lib_mk = mkcache.get_parsed_mk(lib_mk_file)
    #pprint.pprint(lib_mk.debug_struct(), width=180)
    lib_mk.process(build_env)
    #pprint.pprint(build_env.debug_struct('pretty'), width=200)


    ### handle include import-<lib>.mk files
    dep_libs = build_env.var_values('LIBS')
    print("LIBS: %s" % (str(dep_libs)))
    for dep_lib in dep_libs:
        dep_lib_import_mk_file = tools.find_first(repositories, 'lib/import/import-%s.mk' % (dep_lib))
        if dep_lib_import_mk_file is not None:
            print("processing import-%s file: %s" % (dep_lib, dep_lib_import_mk_file))
            dep_lib_import_mk = mkcache.get_parsed_mk(dep_lib_import_mk_file)
            dep_lib_import_mk.process(build_env)


    ### handle include global.mk
    global_mk_file = '%s/mk/global.mk' % (env['BASE_DIR'])
    global_mk = mkcache.get_parsed_mk(global_mk_file)
    global_mk.process(build_env)
    #pprint.pprint(build_env.debug_struct('pretty'), width=200)


    ### handle shared library settings
    symbols_file = build_env.var_value('SYMBOLS')
    if len(symbols_file) > 0:
        build_env.var_set('SHARED_LIB', 'yes')
        build_env.var_set('ABI-SO', '%s.abi.so' % (lib_name))

        ### TODO - symbols link file
        # $(LIB).symbols:
        #    $(VERBOSE)ln -sf $(SYMBOLS) $@
        ### handle <lib>.symbols.s


    ### handle libgcc
    # TODO cache results or maybe set unconditionally
    if build_env.check_var('SHARED_LIB'):
        ##LIBGCC = $(shell $(CC) $(CC_MARCH) -print-libgcc-file-name)
        cmd = "%s %s -print-libgcc-file-name" % (build_env.var_value('CC'),
                                                 build_env.var_value('CC_MARCH'))
        results = subprocess.run(cmd,
                                 stdout=subprocess.PIPE,
                                 shell=True, universal_newlines=True, check=True)
        output = results.stdout
        build_env.var_set('LIBGCC', output)



    pprint.pprint(build_env.debug_struct('pretty'), width=200)


    ### handle include generic.mk functionality




    return

    # $(VERBOSE)$(CXX) $(CXX_DEF) $(CC_CXX_OPT) $(INCLUDES) -c $< -o $@

    localEnv = env.Clone()

    localEnv['CXX'] = '/usr/local/genode/tool/19.05/bin/genode-x86-g++'

    localEnv.AppendUnique(CPPPATH=['#repos/base/src/include'])
    localEnv.AppendUnique(CPPPATH=['#repos/base/include'])
    localEnv.AppendUnique(CPPPATH=['#repos/base/include/spec/64bit'])
    localEnv.AppendUnique(CPPPATH=['#repos/base/include/spec/x86_64'])
    localEnv.AppendUnique(CPPPATH=['#repos/base/include/spec/x86'])
    
    localEnv.Append(CXXFLAGS='-ffunction-sections -fno-strict-aliasing')
    localEnv.Append(CXXFLAGS='-ffunction-sections -fno-strict-aliasing')
    
    obj = localEnv.SharedObject(source = '#repos/base/src/lib/cxx/emutls.cc', target = 'emutls.o')

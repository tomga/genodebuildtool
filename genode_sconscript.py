
import glob

# debug support
import pprint

# buildtoool packages
import mkevaluator
import mkparser
import mklogparser

import genode_tools as tools


def sconscript(env):

    build_dir = env['BUILD']
    process_builddir(build_dir, env)


parser = mkparser.initialize()
mkcache = mkevaluator.MkCache(parser)


def process_builddir(build_dir, env):
    """Process build targets for given build directory.

    Mimics behavior of tool/builddir/build.mk
    """

    build_conf = mkcache.get_parsed_mk('%s/etc/build.conf' % (build_dir))

    build_env = mkevaluator.MkEnv(mkcache)
    build_conf.process(build_env)
    #pprint.pprint(build_env.debug_struct('pretty'), width=200)

    repositories = build_env.var_values('REPOSITORIES')

    # handle */etc/specs.conf files
    repositories_specs_conf_files = tools.find_files('%s/etc/specs.conf', repositories)
    specs_conf_files = repositories_specs_conf_files + ['%s/etc/specs.conf' % (build_dir)]
    print("specs files: %s" % (str(specs_conf_files)))
    for specs_conf_file in specs_conf_files:
        specs_conf = mkcache.get_parsed_mk(specs_conf_file)
        specs_conf.process(build_env)
    pprint.pprint(build_env.debug_struct('pretty'), width=200)


    # handle mk/spec/$(SPEC).mk files
    #
    # NOTE: it is suspicious that only first found mk/spec/$(SPEC).mk
    #       file is included - there is no easily visible rule to know
    #       which is selected but currently just mimic behaviour from
    #       build.mk
    specs = build_env.var_values('SPECS')
    base_dir = build_env.var_value('BASE_DIR')
    print("SPECS: %s" % (specs))
    specs_mk_files = []
    for spec in specs:
        specs_mk_file = tools.find_first(repositories, 'mk/spec/%s.mk' % (spec))
        if specs_mk_file is not None:
            specs_mk_files += [specs_mk_file]

    base_specs_mk_files = tools.find_files(base_dir + '/mk/spec/%s.mk', specs)
    specs_mk_files = list(set(specs_mk_files + base_specs_mk_files))

    print("<spec>.mk files: %s" % (str(specs_mk_files)))
    for specs_mk_file in specs_mk_files:
        specs_mk = mkcache.get_parsed_mk(specs_mk_file)
        specs_mk.process(build_env)
    pprint.pprint(build_env.debug_struct('pretty'), width=200)


    localEnv = env.Clone()

    localEnv.AppendUnique(CPPPATH=['#repos/base/src/include'])
    localEnv.AppendUnique(CPPPATH=['#repos/base/include'])
    localEnv.AppendUnique(CPPPATH=['#repos/base/include/spec/64bit'])
    localEnv.AppendUnique(CPPPATH=['#repos/base/include/spec/x86_64'])
    localEnv.AppendUnique(CPPPATH=['#repos/base/include/spec/x86'])
    
    localEnv['CXX'] = '/usr/local/genode/tool/19.05/bin/genode-x86-g++'
    localEnv.Append(CXXFLAGS='-ffunction-sections -fno-strict-aliasing')
    localEnv.Append(CXXFLAGS='-ffunction-sections -fno-strict-aliasing')
    
    obj = localEnv.SharedObject(source = '#repos/base/src/lib/cxx/emutls.cc', target = 'emutls.o')



import glob
import os
import re
import subprocess

# debug support
import pprint

# buildtool packages
import buildtool_tools
import mkevaluator
import mkparser
import mklogparser

import genode_lib
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


    genode_dir = build_env.var_value('GENODE_DIR')
    env['GENODE_DIR'] = genode_dir

    genode_localization_pattern = re.compile('^%s/' % (env['GENODE_DIR']))
    env['fn_localize_path'] = lambda path: genode_localization_pattern.sub('', path)
    env['fn_sconsify_path'] = lambda path: genode_localization_pattern.sub('#', path)
    genode_prettify_pattern = re.compile('^.*/var/libcache/')
    env['fn_prettify_path'] = lambda path: genode_prettify_pattern.sub('', str(path))

    def format_message_simple(tgt, src, cmd_pres, cmd_var, e):
        return "%s %s" % (cmd_pres, genode_prettify_pattern.sub('', str(tgt)))

    #processed_messages = set([])
    #def format_message_verbose(tgt, src, cmd_pres, cmd_var, e):
    #    tgt_str = str(tgt)
    #    if tgt_str in processed_messages:
    #        return " " # ugly hack to avoid duplicated messages
    #    processed_messages.add(tgt_str)
    #    return "%s %s%s" % (cmd_pres,
    #                        genode_prettify_pattern.sub('', tgt_str),
    #                        "\n%s" % (e.subst(e[cmd_var], raw=0,
    #                                          target=tgt, source=src)))

    def format_message_verbose(tgt, src, cmd_pres, cmd_var, e):
        return "%s %s\n%s" % (cmd_pres,
                              genode_prettify_pattern.sub('', str(tgt)),
                              e.subst(e[cmd_var], raw=0, target=tgt, source=src))
    env['fn_msg'] = format_message_simple if not env['VERBOSE_OUTPUT'] else format_message_verbose
    env['SHCXXCOMSTR']  = '${fn_msg(TARGET, SOURCES, " COMPILE ", "SHCXXCOM",  __env__)}'
    env['SHCCCOMSTR']   = '${fn_msg(TARGET, SOURCES, " COMPILE ", "SHCCCOM",   __env__)}'
    env['ASPPCOMSTR']   = '${fn_msg(TARGET, SOURCES, " ASSEMBLE", "ASPPCOM",   __env__)}'
    env['ASCOMSTR']     = '${fn_msg(TARGET, SOURCES, " ASSEMBLE", "ASCOM",     __env__)}'
    env['ARCOMSTR']     = '${fn_msg(TARGET, SOURCES, " LINK    ", "ARCOM",     __env__)}'
    env['MERGECOMSTR']  = '${fn_msg(TARGET, SOURCES, " MERGE   ", "MERGECOM",  __env__)}'
    env['OBJCPYCOMSTR'] = '${fn_msg(TARGET, SOURCES, " CONVERT ", "OBJCPYCOM", __env__)}'

    repositories = build_env.var_values('REPOSITORIES')
    env['REPOSITORIES'] = repositories

    base_dir = build_env.var_value('BASE_DIR')
    env['BASE_DIR'] = base_dir

    lib_cache_dir = build_env.var_value('LIB_CACHE_DIR')
    env['LIB_CACHE_DIR'] = lib_cache_dir

    ### handle */etc/specs.conf files
    repositories_specs_conf_files = tools.find_files('%s/etc/specs.conf', repositories)
    specs_conf_files = repositories_specs_conf_files + ['%s/etc/specs.conf' % (build_dir)]
    env['fn_info']("processing specs files: %s" % (str(specs_conf_files)))
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
    env['fn_debug']("SPECS: %s" % (specs))
    specs_mk_files = []
    for spec in specs:
        specs_mk_file, specs_mk_repo = tools.find_first(repositories, 'mk/spec/%s.mk' % (spec))
        if specs_mk_file is not None:
            specs_mk_files += [specs_mk_file]

    base_specs_mk_files = tools.find_files(base_dir + '/mk/spec/%s.mk', specs)
    specs_mk_files = list(set(specs_mk_files + base_specs_mk_files))

    env['fn_info']("processing <spec>.mk files: %s" % (str(specs_mk_files)))
    for specs_mk_file in specs_mk_files:
        specs_mk = mkcache.get_parsed_mk(specs_mk_file)
        specs_mk.process(build_env)
    #pprint.pprint(build_env.debug_struct('pretty'), width=200)

    specs = build_env.var_values('SPECS')
    env['fn_debug']("SPECS: %s" % (specs))
    env['SPECS'] = specs


    ### handle global.mk
    #
    # NOTE: it seems it is included only for CUSTOM_CXX_LIB and
    #       including it here is too early for evaluating some
    #       variables like e.g. CC_OPT_NOSTDINC as their value depend
    #       on values included in library specifi files so currently
    #       evaluating to temporary env and later it can be considered
    #       to do something more specific
    temp_build_env = mkevaluator.MkEnv(mkcache, parent_env=build_env)
    base_global_mk = mkcache.get_parsed_mk('%s/mk/global.mk' % (base_dir))
    base_global_mk.process(temp_build_env)
    #pprint.pprint(temp_build_env.debug_struct('pretty'), width=200)
    ## temp_build_env.var_set('CUSTOM_CXX_LIB', '/usr/local/genode/tool/19.05/bin/genode-x86-g++')


    ### handle LIBGCC_INC_DIR
    #
    # NOTE: probably it should be moved before processing global.mk as
    #       it is appended there to ALL_INC_DIR; in recursive make
    #       case it gets included there later
    ##export LIBGCC_INC_DIR = $(shell dirname `$(CUSTOM_CXX_LIB) -print-libgcc-file-name`)/include
    cmd = "%s -print-libgcc-file-name" % (temp_build_env.var_value('CUSTOM_CXX_LIB')),
    results = subprocess.run(cmd, stdout=subprocess.PIPE,
                             shell=True, universal_newlines=True, check=True)
    output = results.stdout
    build_env.var_set('LIBGCC_INC_DIR', '%s/include' % (os.path.dirname(output)))
    #pprint.pprint(build_env.debug_struct('pretty'), width=200)



    def lib_alias_name(lib_name):
        return '%s:%s' % (lib_name, build_dir)
    env['fn_lib_alias_name'] = lib_alias_name

    required_libs = []
    known_libs = set([])
    def require_libs(dep_libs):
        dep_aliases = []
        for dep in dep_libs:
            if dep not in known_libs:
                known_libs.add(dep)
                required_libs.append(dep)
            dep_aliases.append(env.Alias(lib_alias_name(dep)))
        return dep_aliases
    env['fn_require_libs'] = require_libs



    require_libs(env['LIB'].split())

    libs = []
    while len(libs) < len(required_libs):
        libs.append(process_lib(required_libs[len(libs)], env, build_env))

    #libs.append(process_lib('cxx', env, build_env))
    #libs.append(process_lib('syscall-linux', env, build_env))
    #libs.append(process_lib('base-linux-common', env, build_env))

    env.Default(libs)

    env['fn_debug'](env.Dump())


def process_lib(lib_name, env, build_env):
    """Process library build rules.

    Build rules are read from <lib>.mk file like in standard Genode
    build (repos/<repo>/lib/mk/<lib>.mk) but there are possibilities
    to overwrite default with providing build rules in
    <buildtool>/genode/repos/<repo>/lib/mk/<lib>.py file where <repo>
    must be the same as for found <lib>.mk file.
    """

    repositories = env['REPOSITORIES']
    specs = env['SPECS']

    ## find <lib>.mk file with repo
    lib_mk_file = None
    lib_mk_repo = None
    for repository in repositories:
        for spec in specs:
            test_mk_file = 'lib/mk/spec/%s/%s.mk' % (spec, lib_name)
            if tools.is_repo_file(test_mk_file, repository):
                lib_mk_file = tools.file_path(test_mk_file, repository)
                lib_mk_repo = repository
                break
        if lib_mk_file is not None:
            break

        test_mk_file = 'lib/mk/%s.mk' % (lib_name)
        if tools.is_repo_file(test_mk_file, repository):
            lib_mk_file = tools.file_path(test_mk_file, repository)
            lib_mk_repo = repository
            break

    ## find <lib>.sc file with repo
    lib_sc_file = None
    lib_sc_repo = None
    for repository in repositories:
        for spec in specs:
            test_sc_file = 'lib/mk/spec/%s/%s.sc' % (spec, lib_name)
            if tools.is_repo_file(test_sc_file, repository):
                lib_sc_file = tools.file_path(test_sc_file, repository)
                lib_sc_repo = repository
                break
        if lib_sc_file is not None:
            break

        test_sc_file = 'lib/mk/%s.sc' % (lib_name)
        if tools.is_repo_file(test_sc_file, repository):
            lib_sc_file = tools.file_path(test_sc_file, repository)
            lib_sc_repo = repository
            break

    if (lib_mk_file is None and lib_sc_file is None):
        print("Build rules file not found for library '%s'" % (lib_name))
        quit()

    if (lib_mk_file is not None and lib_sc_file is not None):
        print("Multiple build rules files found for library '%s' ('%s' and '%s')"
              % (lib_name,
                 tools.file_path(lib_mk_file, lib_mk_repo),
                 tools.file_path(lib_sc_file, lib_sc_repo)))
        quit()

    if lib_sc_file is not None:
        print("lib_sc_file: %s" % (lib_sc_file))
        print("TODO: support needed")
        quit()
    else:
        env['fn_debug']("lib_mk_file: %s" % (lib_mk_file))
        overlay_file_path = check_for_lib_mk_overlay(lib_name, env, lib_mk_file, lib_mk_repo)
        if overlay_file_path is None:
            lib = genode_lib.GenodeMkLib(lib_name, env,
                                         lib_mk_file, lib_mk_repo,
                                         build_env)
            return lib.process()
        else:
            process_lib_overlay_fun = buildtool_tools.get_process_lib_overlay_fun(overlay_file_path)
            return process_lib_overlay_fun(lib_name, env, lib_mk_file, lib_mk_repo, build_env)
            #from genode.repos.base.lib.mk.cxx0 import process_lib_overlay
            #process_lib_overlay(lib_name, env, lib_mk_file, lib_mk_repo, build_env)

            #process_lib_overlay(lib_name, env, lib_mk_file, lib_mk_repo, build_env)


def check_for_lib_mk_overlay(lib_name, env, lib_mk_file, lib_mk_repo):
    """Looks for library"""

    full_mk_file_path = tools.file_path(lib_mk_file, lib_mk_repo)
    mk_file_path = env['fn_localize_path'](full_mk_file_path)

    mk_pattern = re.compile(r'\.mk$')
    overlay_info_file_path = os.path.join(env['OVERLAYS_DIR'], mk_pattern.sub('.ovr', mk_file_path))
    #print("Checking overlays info file %s" % (overlay_info_file_path))
    if not os.path.isfile(overlay_info_file_path):
        # no overlays info file - fallback to default mk processing
        return

    env['fn_info']("Found overlays info file %s" % (overlay_info_file_path))

    mk_file_md5 = tools.file_md5(mk_file_path)
    env['fn_info']("library mk '%s' hash: '%s'" % (mk_file_path, mk_file_md5))

    overlay_file_name = None
    with open(overlay_info_file_path, "r") as f:
        for line in f:
            if line.startswith(mk_file_md5):
                ovr_data = line.split()
                if len(ovr_data) < 2:
                    print("ERROR: invalid overlay entry in '%s':" % (overlay_info_file_path))
                    print("     : %s" % (line))
                    quit()
                overlay_file_name = ovr_data[1]
    if overlay_file_name is None:
        print("ERROR: overlay not found in '%s' for hash '%s':" % (overlay_info_file_path, mk_file_md5))
        quit()

    overlay_file_path = os.path.join(os.path.dirname(overlay_info_file_path), overlay_file_name)

    #print("Checking overlay file %s" % (overlay_file_path))
    if not os.path.isfile(overlay_file_path):
        print("ERROR: missing overlay file '%s' mentioned metioned  in '%s':" % (overlay_file_path, overlay_info_file_path))
        quit()

    env['fn_notice']("Found overlay file '%s' for mk '%s'" % (overlay_file_path, mk_file_path))
    return overlay_file_path


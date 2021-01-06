
import glob
import os
import re
import subprocess

# debug support
import pprint

# buildtool packages
from gscons import buildtool_tools
from gscons import mkevaluator
from gscons import mkparser
from gscons import scmkevaluator

from gscons import genode_lib
from gscons import genode_prog
from gscons import genode_tools as tools

from gscons import genode_util_mk_functions
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

    if not os.path.isfile(os.path.join(build_dir, 'SCons')):
        print("Specified build directory: '%s' is not marked to be used used by SCons (missing SCons file). Quit." % (build_dir))
        quit()

    scmkcache = scmkevaluator.ScMkCache(env, mkcache)
    build_env = mkevaluator.MkEnv(scmkcache)

    if 'BOARD' in env:
        build_env.var_set('BOARD', env['BOARD'])
    if 'KERNEL' in env:
        build_env.var_set('KERNEL', env['KERNEL'])

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
    env['fn_sconsify_path'] = lambda path: '#' + env['fn_localize_path'](path) if not path.startswith('/') else path
    env['fn_unsconsify_path'] = lambda path: path[1:] if path.startswith('#') else path
    genode_prettify_lib_pattern = re.compile('^%s/var/libcache/' % (build_dir))
    genode_prettify_prog_pattern = re.compile('^%s/' % (build_dir))
    def prettify_path(path):
        p = str(path)
        p = genode_prettify_lib_pattern.sub('lib/', p)
        p = genode_prettify_prog_pattern.sub('', p)
        return p
    env['fn_prettify_path'] = prettify_path

    def format_message_simple(tgt, src, cmd_pres, cmd_var, e):
        return "%s %s" % (cmd_pres, prettify_path(tgt))

    def format_message_verbose(tgt, src, cmd_pres, cmd_var, e):
        return "%s %s\n%s" % (cmd_pres,
                              prettify_path(tgt),
                              e.subst(e[cmd_var], raw=0, target=tgt, source=src))
    env['fn_msg'] = format_message_simple if not env['VERBOSE_OUTPUT'] else format_message_verbose
    env['SHCXXCOMSTR']  = '${fn_msg(TARGET, SOURCES, " COMPILE ", "SHCXXCOM",  __env__)}'
    env['SHCCCOMSTR']   = '${fn_msg(TARGET, SOURCES, " COMPILE ", "SHCCCOM",   __env__)}'
    env['ASPPCOMSTR']   = '${fn_msg(TARGET, SOURCES, " ASSEMBLE", "ASPPCOM",   __env__)}'
    env['ASCOMSTR']     = '${fn_msg(TARGET, SOURCES, " ASSEMBLE", "ASCOM",     __env__)}'
    env['ARCOMSTR']     = '${fn_msg(TARGET, SOURCES, " LINK    ", "ARCOM",     __env__)}'
    env['MERGECOMSTR']  = '${fn_msg(TARGET, SOURCES, " MERGE   ", "MERGECOM",  __env__)}'
    env['OBJCPYCOMSTR'] = '${fn_msg(TARGET, SOURCES, " CONVERT ", "OBJCPYCOM", __env__)}'
    env['LINKCOMSTR']   = '${fn_msg(TARGET, SOURCES, " LINK    ", "LINKCOM",   __env__)}'
    env['BUILDCOMSTR']  = '${fn_msg(TARGET, SOURCES, " BUILD   ", "BUILDCOM",  __env__)}'

    def format_custom_message_simple(tgt, cmd_pres, cmd_text):
        return "%s %s" % (' ' + cmd_pres.ljust(8), prettify_path(tgt))

    def format_custom_message_verbose(tgt, cmd_pres, cmd_text):
        return "%s %s\n%s" % (' ' + cmd_pres.ljust(8), prettify_path(tgt), cmd_text)

    env['fn_fmt_out'] = (format_custom_message_simple if not env['VERBOSE_OUTPUT']
                         else format_custom_message_verbose)

    overlay_localization_pattern = re.compile('^%s/' % (env['OVERLAYS_DIR']))
    env['fn_localize_ovr'] = lambda path: overlay_localization_pattern.sub('<overlays>/', path)


    lib_info_dict = {}
    def register_lib_info(lib_name, lib_info):
        env['fn_debug']('register_lib_info: %s, %s' % (lib_name, str(lib_info)))
        assert lib_name not in lib_info_dict
        lib_info_dict[lib_name] = lib_info
    env['fn_register_lib_info'] = register_lib_info

    def get_lib_info(lib_name):
        assert lib_name in lib_info_dict, 'get_lib_info: not found info for "%s"' % lib_name
        lib_info = lib_info_dict[lib_name]
        env['fn_debug']('get_lib_info: %s, %s' % (lib_name, str(lib_info)))
        return lib_info
    env['fn_get_lib_info'] = get_lib_info


    repositories = build_env.var_values('REPOSITORIES')
    env['REPOSITORIES'] = repositories

    base_dir = build_env.var_value('BASE_DIR')
    env['BASE_DIR'] = base_dir

    install_dir = build_env.var_value('INSTALL_DIR')
    env['INSTALL_DIR'] = install_dir

    debug_dir = build_env.var_value('DEBUG_DIR')
    env['DEBUG_DIR'] = debug_dir

    lib_cache_dir = build_env.var_value('LIB_CACHE_DIR')
    env['LIB_CACHE_DIR'] = lib_cache_dir

    env['CHECK_ABI'] = env['fn_localize_path']('%s/../../tool/check_abi' % (base_dir))

    ### handle */etc/specs.conf files
    repositories_specs_conf_files = tools.find_files('%s/etc/specs.conf', repositories)
    specs_conf_files = repositories_specs_conf_files + ['%s/etc/specs.conf' % (build_dir)]
    env['fn_info']("Processing specs files: %s" %
                   (' '.join(list(map(env['fn_localize_path'], specs_conf_files)))))
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
    if 'BOARD' in env and env['BOARD'] not in specs:
        specs.append(env['BOARD'])
        build_env.var_set('SPECS', ' '.join(specs))
    env['fn_debug']("SPECS: %s" % (specs))
    specs_mk_files = []
    for spec in specs:
        specs_mk_file, specs_mk_repo = tools.find_first(repositories, 'mk/spec/%s.mk' % (spec))
        if specs_mk_file is not None:
            specs_mk_files += [specs_mk_file]

    base_specs_mk_files = tools.find_files(base_dir + '/mk/spec/%s.mk', specs)
    all_specs_mk_files = []
    for specs_mk_file in specs_mk_files + base_specs_mk_files:
        if specs_mk_file not in all_specs_mk_files:
            all_specs_mk_files.append(specs_mk_file)

    env['fn_info']("Processing <spec>.mk files: %s"
                   % (' '.join(list(map(env['fn_localize_path'], all_specs_mk_files)))))
    for specs_mk_file in all_specs_mk_files:
        specs_mk = mkcache.get_parsed_mk(specs_mk_file)
        specs_mk.process(build_env)
    #pprint.pprint(build_env.debug_struct('pretty'), width=200)

    specs = build_env.var_values('SPECS')
    env['fn_info']("Effective specs: %s" % (' '.join(specs)))
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
    output = results.stdout.strip()
    build_env.var_set('LIBGCC_INC_DIR', '%s/include' % (os.path.dirname(output)))
    #pprint.pprint(build_env.debug_struct('pretty'), width=200)



    def lib_alias_name(lib_name):
        return 'LIB:%s:%s' % (build_dir, lib_name)
    env['fn_lib_alias_name'] = lib_alias_name

    libs = []
    known_libs = set([])
    def require_libs(dep_libs):
        dep_aliases = []
        for dep in dep_libs:
            if dep not in known_libs:
                known_libs.add(dep)
                libs.extend(process_lib(dep, env, build_env))
            dep_aliases.append(env.Alias(lib_alias_name(dep)))
        return dep_aliases
    env['fn_require_libs'] = require_libs



    def prog_alias_name(prog_name):
        return 'PRG:%s:%s' % (build_dir, prog_name)
    env['fn_prog_alias_name'] = prog_alias_name

    progs = []
    known_progs = set([])
    def require_progs(dep_progs):
        dep_aliases = []
        for dep in dep_progs:
            if dep not in known_progs:
                progs.extend(process_progs(dep, env, build_env, known_progs))
            dep_aliases.append(env.Alias(prog_alias_name(dep)))
        return dep_aliases
    env['fn_require_progs'] = require_progs


    # expand targets lib masks taking into account target excludes
    exp_libs = tools.expand_lib_targets(env['REPOSITORIES'], env['SPECS'],
                                        env['LIB_TARGETS'], env['LIB_EXCLUDES'])
    env['LIB_TARGETS'] = exp_libs
    env['fn_info']("Effective library targets: %s" % (' '.join(exp_libs)))

    # expand targets prog masks taking into account target excludes
    exp_progs = tools.expand_prog_targets(env['REPOSITORIES'],
                                          env['PROG_TARGETS'], env['PROG_EXCLUDES'])
    env['PROG_TARGETS'] = exp_progs
    env['fn_info']("Effective program targets: %s" % (' '.join(exp_progs)))

    if env['DEV_ONLY_EXPAND_TARGETS']:
        print('LIBS: %s' % (' '.join(exp_libs)))
        print('PROGS: %s' % (' '.join(exp_progs)))
        quit()

    require_libs(env['LIB_TARGETS'])
    require_progs(env['PROG_TARGETS'])

    env['fn_debug']('BUILD_TARGETS: %s' % (str(env['BUILD_TARGETS'])))
    targets = libs + progs
    env['BUILD_TARGETS'] += targets
    env['fn_info']('Final build targets: %s' % (' '.join(list(map(str, env['BUILD_TARGETS'])))))

    env['fn_trace'](env.Dump())



def process_lib(lib_name, env, build_env):
    """Process library build rules.

    Build rules are read from <lib>.mk file like in standard Genode
    build (repos/<repo>/lib/mk/<lib>.mk) but there are possibilities
    to overwrite default with providing build rules in
    <buildtool>/genode/repos/<repo>/lib/mk/<lib>.mk.ovr file where <repo>
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

    overlay_info_file_path = os.path.join(env['OVERLAYS_DIR'], '%s.ovr' % (mk_file_path))
    #print("Checking overlays info file %s" % (overlay_info_file_path))
    if not os.path.isfile(overlay_info_file_path):
        # no overlays info file - fallback to default mk processing
        return

    env['fn_info']("Found overlays info file %s" %
                   (env['fn_localize_ovr'](overlay_info_file_path)))

    mk_file_md5 = tools.file_md5(mk_file_path)
    env['fn_debug']("library mk '%s' hash: '%s'" % (mk_file_path, mk_file_md5))

    overlay_file_name = None
    with open(overlay_info_file_path, "r") as f:
        for line in f:
            if line.startswith(mk_file_md5):
                ovr_data = line.split()
                if len(ovr_data) < 2:
                    env['fn_error']("Invalid overlay entry in '%s':"
                                    % (env['fn_localize_ovr'](overlay_info_file_path)))
                    print("     : %s" % (line))
                    quit()
                overlay_file_name = ovr_data[1]
    if overlay_file_name is None:
        env['fn_error']("Overlay not found in '%s' for hash '%s':" %
                        (env['fn_localize_ovr'](overlay_info_file_path), mk_file_md5))
        quit()

    overlay_file_path = os.path.join(os.path.dirname(overlay_info_file_path), overlay_file_name)
    overlay_type = os.path.splitext(overlay_file_path)[1]

    env['fn_debug']("Checking overlay file %s" % (overlay_file_path))
    if overlay_type != '.orig' and not os.path.isfile(overlay_file_path):
        env['fn_error']("Missing overlay file '%s' mentioned metioned  in '%s':" %
                        (env['fn_localize_ovr'](overlay_file_path),
                         env['fn_localize_ovr'](overlay_info_file_path)))
        quit()

    env['fn_notice']("Using overlay file '%s' for mk '%s'" %
                     (env['fn_localize_ovr'](overlay_file_path), mk_file_path))

    if overlay_type in ['.mk', '.patch', '.orig']:
        env['fn_notice']("Overlay type is mk so fallback to use standard mk processing")
        return

    return overlay_file_path


def process_progs(prog_name, env, build_env, known_progs):

    repositories = env['REPOSITORIES']
    env['fn_debug']('process_progs: %s, repositories: %s' % (prog_name, repositories))

    target_descr_files = {}

    for repository in repositories:
        mk_list = glob.glob('%s/src/%s/**/target.mk' % (repository, prog_name), recursive=True)
        for mk in mk_list:
            prog_path = mk[len('%s/src/' % (repository)):-len('/target.mk')]
            env['fn_debug']('prog_path: %s' % (prog_path))
            if prog_path in target_descr_files:
                print("Multiple build rules files found for program '%s' ('%s' and '%s')"
                      % (prog_name, target_descr_files[prog_path][1], mk))
                quit()
            target_descr_files[prog_path] = ['mk', mk, repository]

        sc_list = glob.glob('%s/src/%s/**/target.sc' % (repository, prog_name), recursive=True)
        for sc in sc_list:
            prog_path = sc[len('%s/src/' % (repository)):-len('/target.sc')]
            print('prog_path: %s' % (prog_path))
            if prog_path in target_descr_files:
                print("Multiple build rules files found for program '%s' ('%s' and '%s')"
                      % (prog_name, target_descr_files[prog_path][1], sc))
                quit()
            target_descr_files[prog_path] = ['sc', sc, repository]

    env['fn_debug']('process_progs: %s, found descr files: %s' % (prog_name, str(target_descr_files)))

    progs = []
    for prog, desc in target_descr_files.items():
        prog_mk_file = desc[1] if desc[0] == 'mk' else None
        prog_mk_repo = desc[2] if desc[0] == 'mk' else None
        prog_sc_file = desc[1] if desc[0] == 'sc' else None
        prog_sc_repo = desc[2] if desc[0] == 'sc' else None

        if prog in known_progs:
            continue
        known_progs.add(prog)

        progs.extend(process_prog(prog,
                                  prog_mk_file, prog_mk_repo,
                                  prog_sc_file, prog_sc_repo,
                                  env, build_env))

    return progs



def process_prog(prog_name,
                 prog_mk_file, prog_mk_repo,
                 prog_sc_file, prog_sc_repo,
                 env, build_env):
    """Process program build rules.

    Build rules are read from <prog>/target.mk file like in standard
    Genode build (repos/<repo>/src/<prog>/target.mk) but there are
    possibilities to overwrite default with providing build rules in
    <buildtool>/genode/repos/<repo>/src/<prog>/mk/<prog>.ovr file where
    <repo> must be the same as for found <prog>/target.mk file.
    """

    repositories = env['REPOSITORIES']


    if prog_sc_file is not None:
        print("prog_sc_file: %s" % (prog_sc_file))
        print("TODO: support needed")
        quit()
    else:
        env['fn_debug']("prog_mk_file: %s" % (prog_mk_file))
        overlay_file_path = check_for_prog_mk_overlay(prog_name, env, prog_mk_file, prog_mk_repo)
        if overlay_file_path is None:
            prog = genode_prog.GenodeMkProg(prog_name, env,
                                            prog_mk_file, prog_mk_repo,
                                            build_env)
            return prog.process()
        else:
            process_prog_overlay_fun = buildtool_tools.get_process_prog_overlay_fun(overlay_file_path)
            return process_prog_overlay_fun(prog_name, env, prog_mk_file, prog_mk_repo, build_env)


def check_for_prog_mk_overlay(prog_name, env, prog_mk_file, prog_mk_repo):
    """Looks for program"""

    full_mk_file_path = tools.file_path(prog_mk_file, prog_mk_repo)
    mk_file_path = env['fn_localize_path'](full_mk_file_path)

    overlay_info_file_path = os.path.join(env['OVERLAYS_DIR'], '%s.ovr' % (mk_file_path))
    #print("Checking overlays info file %s" % (overlay_info_file_path))
    if not os.path.isfile(overlay_info_file_path):
        # no overlays info file - fallback to default mk processing
        return

    env['fn_info']("Found overlays info file %s" %
                   (env['fn_localize_ovr'](overlay_info_file_path)))

    mk_file_md5 = tools.file_md5(mk_file_path)
    env['fn_debug']("program mk '%s' hash: '%s'" % (mk_file_path, mk_file_md5))

    overlay_file_name = None
    with open(overlay_info_file_path, "r") as f:
        for line in f:
            if line.startswith(mk_file_md5):
                ovr_data = line.split()
                if len(ovr_data) < 2:
                    env['fn_error']("Invalid overlay entry in '%s':" %
                                    (env['fn_localize_ovr'](overlay_info_file_path)))
                    print("     : %s" % (line))
                    quit()
                overlay_file_name = ovr_data[1]
    if overlay_file_name is None:
        env['fn_error']("Overlay not found in '%s' for hash '%s':" %
                        (env['fn_localize_ovr'](overlay_info_file_path), mk_file_md5))
        quit()

    overlay_file_path = os.path.join(os.path.dirname(overlay_info_file_path), overlay_file_name)
    overlay_type = os.path.splitext(overlay_file_path)[1]

    env['fn_debug']("Checking overlay file %s" % (overlay_file_path))
    if overlay_type != '.orig' and not os.path.isfile(overlay_file_path):
        env['fn_error']("Missing overlay file '%s' mentioned metioned  in '%s':"
                        % (env['fn_localize_ovr'](overlay_file_path),
                           env['fn_localize_ovr'](overlay_info_file_path)))
        quit()

    env['fn_notice']("Using overlay file '%s' for mk '%s'" %
                     (env['fn_localize_ovr'](overlay_file_path), mk_file_path))

    if overlay_type in ['.mk', '.patch', '.orig']:
        env['fn_notice']("Overlay type is mk so fallback to use standard mk processing")
        return

    return overlay_file_path


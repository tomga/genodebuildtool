
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

from gscons import genode_all_target
from gscons import genode_port
from gscons import genode_lib
from gscons import genode_prog
from gscons import genode_run
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

    abs_build_dir = os.path.abspath(build_dir)

    build_env.var_set('BUILD_BASE_DIR', '%s' % (abs_build_dir))

    env['DEBUG_DIR'] = '%s/debug' % (build_dir)
    build_env.var_set('DEBUG_DIR', '%s/debug' % (abs_build_dir))

    env['INSTALL_DIR'] = '%s/bin' % (build_dir)
    build_env.var_set('INSTALL_DIR', '%s/bin' % (abs_build_dir))

    env['LIB_CACHE_DIR'] = '%s/var/libcache' % (build_dir)
    build_env.var_set('LIB_CACHE_DIR', '%s/var/libcache' % (abs_build_dir))

    env['RUN_LOG_DIR'] = '%s/runlog' % (build_dir)
    env['PORT_LOG_DIR'] = '%s/portlog' % (build_dir)

    print("LIB_CACHE_DIR: %s" % (build_env.var_value('LIB_CACHE_DIR')))

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
    env['RUNCOMSTR']    = '${fn_msg(TARGET, SOURCES, " RUN     ", "RUNCOM",    __env__)}'

    def format_custom_message_simple(tgt, cmd_pres, cmd_text):
        pres_list = [ "%s %s" % (' ' + cmd_pres.ljust(8), prettify_path(tgt)) ]
        def nextpres(tgt, src, e):
            pres = None
            if len(pres_list) != 0:
                pres = pres_list.pop(0)
            return pres
        return nextpres

    def format_custom_message_verbose(tgt, cmd_pres, cmd_text):
        if not isinstance(cmd_text, list):
            cmd_text = [ cmd_text ]
        pres_list = [(tgt, None, x) for x in cmd_text]
        pres_list[0] = (tgt, cmd_pres, cmd_text[0])
        def nextpres(tgt, src, e):
            tgt, cmd_pres, cmd_text = pres_list.pop(0)
            exp_cmd_text = e.subst(cmd_text, raw=0, target=tgt, source=src)
            if cmd_pres is None:
                return exp_cmd_text
            return "%s %s\n%s" % (' ' + cmd_pres.ljust(8), prettify_path(tgt), exp_cmd_text)
        return nextpres

    env['fn_fmt_out'] = (format_custom_message_simple if not env['VERBOSE_OUTPUT']
                         else format_custom_message_verbose)

    overlay_localization_pattern = re.compile('^%s/' % (env['OVERLAYS_DIR']))
    env['fn_localize_ovr'] = lambda path: overlay_localization_pattern.sub('<overlays>/', path)


    # function that registers function for a source that allows to
    # modify compilation flags; it is used to handle cases where in mk
    # build flags are modified by setting variables in a rule like in:
    #   net/ethernet/eth.o: SETUP_SUFFIX="_eth"
    def register_modify_target_opts(env, src_file, modify_fun):
        if 'reg_modify_target_opts' not in env:
            reg = {}
            env['reg_modify_target_opts'] = reg
            def target_modify_opts_fun(src_filename, opts):
                if src_filename not in reg:
                    return None # no modifications
                env['fn_debug']("Found modify_target_opts for %s" % (src_filename))
                return reg[src_filename](opts)
            env['fn_modify_target_opts'] = target_modify_opts_fun
        env['reg_modify_target_opts'][src_file] = modify_fun
    env['fn_register_modify_target_opts'] = register_modify_target_opts

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
    # NOTE: it is currently included only for CUSTOM_CXX_LIB and
    #       ccache handling and including it here is too early for
    #       evaluating some variables like e.g. CC_OPT_NOSTDINC as
    #       their value depend on values included in library specific
    #       files so currently evaluating to temporary env and later
    #       it can be considered to do something more specific
    temp_build_env = mkevaluator.MkEnv(mkcache, parent_env=build_env)
    base_global_mk = mkcache.get_parsed_mk('%s/mk/global.mk' % (base_dir))
    base_global_mk.process(temp_build_env)
    #pprint.pprint(temp_build_env.debug_struct('pretty'), width=200)
    ## temp_build_env.var_set('CUSTOM_CXX_LIB', '/usr/local/genode/tool/19.05/bin/genode-x86-g++')


    # variables for run tool
    env['CROSS_DEV_PREFIX'] = temp_build_env.var_value('CROSS_DEV_PREFIX')
    env['QEMU_OPT'] = temp_build_env.var_value('QEMU_OPT')
    env['RUN_OPT'] = temp_build_env.var_value('RUN_OPT')
    env['CCACHE'] = temp_build_env.var_value('CCACHE')
    env['MAKE'] = 'make' # it seems to be used for depots but they are not supported yet


    if temp_build_env.var_value('CCACHE') == 'yes':
        setup_ccache(env, temp_build_env, build_env)


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



    def port_alias_name(port_name):
        return 'PORT:%s' % (port_name)
    env['fn_port_alias_name'] = port_alias_name

    all_port_objs = {}
    def require_ports(target, dep_ports):
        dep_port_objs = []
        for dep in dep_ports:
            if dep not in all_port_objs:
                all_port_objs[dep] = None
                port_obj = process_port(dep, env, build_env)
                all_port_objs[dep] = port_obj
            else:
                port_obj = all_port_objs[dep]
                if port_obj is None:
                    env['fn_error']("Circular port dependency detected when processing '%s'"
                                    % (dep))
                    quit()
            dep_port_objs.append(port_obj)
        target.add_dep_targets(dep_port_objs)
        return dep_port_objs
    env['fn_require_ports'] = require_ports


    def lib_alias_name(lib_name):
        return 'LIB:%s:%s' % (build_dir, lib_name)
    env['fn_lib_alias_name'] = lib_alias_name

    all_lib_objs = {}
    def require_libs(target, dep_libs):
        dep_lib_objs = []
        for dep in dep_libs:
            if dep not in all_lib_objs:
                all_lib_objs[dep] = None
                lib_obj = process_lib(dep, env, build_env)
                all_lib_objs[dep] = lib_obj
            else:
                lib_obj = all_lib_objs[dep]
                if lib_obj is None:
                    env['fn_error']("Circular library dependency detected when processing '%s'"
                                    % (dep))
                    quit()
            dep_lib_objs.append(lib_obj)
        target.add_dep_targets(dep_lib_objs)
        return dep_lib_objs
    env['fn_require_libs'] = require_libs


    def prog_alias_name(prog_name):
        return 'PRG:%s:%s' % (build_dir, prog_name)
    env['fn_prog_alias_name'] = prog_alias_name

    all_prog_objs = {}
    def require_progs(target, dep_progs):
        dep_prog_objs = {}
        for dep in dep_progs:
            current_dep_prog_objs = process_progs(dep, env, build_env, all_prog_objs)

            for dep_prog_name, dep_prog_obj in current_dep_prog_objs.items():
                if dep_prog_name not in dep_prog_objs:
                    dep_prog_objs[dep_prog_name] = dep_prog_obj
                else:
                    # dependencies in one require_progs call require
                    # program target more than one time using
                    # different require paths
                    env['fn_notice']("Program target %s required more than once in one require call (now by %s)"
                                     % (dep_prog_name, dep))
        dep_objs = list(dep_prog_objs.values())
        target.add_dep_targets(dep_objs)
        return dep_objs
    env['fn_require_progs'] = require_progs



    def run_alias_name(run_name):
        return 'RUN:%s' % (run_name)
    env['fn_run_alias_name'] = run_alias_name

    all_run_objs = {}
    def require_runs(target, dep_runs):
        dep_run_objs = []
        for dep in dep_runs:
            if dep not in all_run_objs:
                all_run_objs[dep] = None
                run_obj = process_run(dep, env, build_env)
                all_run_objs[dep] = run_obj
            else:
                run_obj = all_run_objs[dep]
                if run_obj is None:
                    env['fn_error']("Circular run dependency detected when processing '%s'"
                                    % (dep))
                    quit()
            dep_run_objs.append(run_obj)
        target.add_dep_targets(dep_run_objs)
        return dep_run_objs
    env['fn_require_runs'] = require_runs



    # expand targets port masks taking into account target excludes
    exp_ports = tools.expand_port_targets(env['REPOSITORIES'],
                                          env['PORT_TARGETS'], env['PORT_EXCLUDES'])
    env['PORT_TARGETS'] = exp_ports
    env['fn_info']("Effective port targets: %s" % (' '.join(exp_ports)))

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

    # expand targets run masks taking into account target excludes
    exp_runs = tools.expand_run_targets(env['REPOSITORIES'],
                                        env['RUN_TARGETS'], env['RUN_EXCLUDES'])
    env['RUN_TARGETS'] = exp_runs
    env['fn_info']("Effective run script targets: %s" % (' '.join(exp_runs)))

    if env['DEV_ONLY_EXPAND_TARGETS']:
        print('PORTS: %s' % (' '.join(exp_ports)))
        print('LIBS: %s' % (' '.join(exp_libs)))
        print('PROGS: %s' % (' '.join(exp_progs)))
        print('RUNS: %s' % (' '.join(exp_runs)))
        quit()

    all_target = genode_all_target.GenodeAll(env,
                                             env['PORT_TARGETS'],
                                             env['LIB_TARGETS'],
                                             env['PROG_TARGETS'],
                                             env['RUN_TARGETS'])
    all_target.process_load()


    # process ports
    port_targets = []
    for port_obj in all_port_objs.values():
        env['fn_debug']("Processing port target: %s" % (port_obj.port_name))
        port_obj_targets = port_obj.process_target()
        if port_obj_targets is not None:
            port_targets.extend(port_obj_targets)

    # inform about outdated ports
    outdated_ports = [ port for port in all_port_objs.values() if port.port_outdated() ]
    if len(outdated_ports) > 0:
        env['fn_notice']("Outdated ports detected")
        env['fn_notice']("  tool/ports/prepare_port %s"
                         % (' '.join(map(lambda p: p.port_name, outdated_ports))))

    # process libraries
    lib_targets = []
    for lib_obj in all_lib_objs.values():
        env['fn_debug']("Processing lib target: %s" % (lib_obj.lib_name))
        lib_obj_targets = lib_obj.process_target()
        if lib_obj_targets is not None:
            lib_targets.extend(lib_obj_targets)

    # process programs
    prog_targets = []
    for prog_obj in all_prog_objs.values():
        env['fn_debug']("Processing prog target: %s" % (prog_obj.prog_name))
        prog_obj_targets = prog_obj.process_target()
        if prog_obj_targets is not None:
            prog_targets.extend(prog_obj_targets)

    # process run scripts
    run_targets = []
    for run_obj in all_run_objs.values():
        env['fn_debug']("Processing run target: %s" % (run_obj.run_name))
        run_obj_targets = run_obj.process_target()
        if run_obj_targets is not None:
            run_targets.extend(run_obj_targets)


    env['fn_debug']('BUILD_TARGETS: %s' % (str(env['BUILD_TARGETS'])))
    targets = lib_targets + prog_targets + run_targets
    env['BUILD_TARGETS'] += targets
    env['fn_info']('Final build targets: %s' % (' '.join(list(map(str, env['BUILD_TARGETS'])))))

    env['fn_trace'](env.Dump())



def process_port(port_name, env, build_env):
    """Process port build rules.
    """

    repositories = env['REPOSITORIES']

    found_port_hash_file = None
    for repository in repositories:
        checked_file = os.path.join(repository, 'ports', '%s.hash' % port_name)
        if os.path.exists(checked_file):
            env['fn_debug']('found_port_hash_file: %s' % (str(checked_file)))
            found_port_hash_file = checked_file
            continue

    if found_port_hash_file is None:
        env['fn_debug']("Port hash file not found for port '%s'" % (port_name))
        return genode_port.GenodeDisabledPort(port_name, env,
                                              "port hash file not found")

    port_obj = genode_port.GenodePort(port_name, env, found_port_hash_file, repository)
    port_obj.process_load()
    return port_obj



def process_run(run_name, env, build_env):
    """Process run build rules.
    """

    repositories = env['REPOSITORIES']

    found_run_file = None
    for repository in repositories:
        checked_file = os.path.join(repository, 'run', '%s.run' % run_name)
        if os.path.exists(checked_file):
            env['fn_debug']('found_run_file: %s' % (str(checked_file)))
            found_run_file = checked_file
            continue

    if found_run_file is None:
        env['fn_debug']("Run file not found for run '%s'" % (run_name))
        return genode_run.GenodeDisabledRun(run_name, env,
                                            "run file not found")

    run_obj = genode_run.GenodeRun(run_name, env, found_run_file, repository)
    run_obj.process_load()
    return run_obj



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
        env['fn_debug']("Build rules file not found for library '%s'" % (lib_name))
        return genode_lib.GenodeDisabledLib(lib_name, env,
                                            "build rules file not found")

    if (lib_mk_file is not None and lib_sc_file is not None):
        env['fn_debug']("Multiple build rules files found for library '%s' ('%s' and '%s')"
                        % (lib_name,
                           tools.file_path(lib_mk_file, lib_mk_repo),
                           tools.file_path(lib_sc_file, lib_sc_repo)))
        return genode_lib.GenodeDisabledLib(lib_name, env,
                                            "multiple build rules variant files found")

    if lib_sc_file is not None:
        env['fn_error']("lib_sc_file: %s" % (lib_sc_file))
        env['fn_error']("TODO: support needed")
        quit()
    else:
        env['fn_debug']("lib_mk_file: %s" % (lib_mk_file))
        overlay_file_path = check_for_lib_mk_overlay(lib_name, env, lib_mk_file, lib_mk_repo)
        if overlay_file_path is None:
            lib_obj = genode_lib.GenodeMkLib(lib_name, env,
                                             lib_mk_file, lib_mk_repo,
                                             build_env)
            lib_obj.process_load()
        else:
            process_lib_overlay_fun = buildtool_tools.get_process_lib_overlay_fun(overlay_file_path)

            # process load
            lib_obj = process_lib_overlay_fun(lib_name, env, lib_mk_file, lib_mk_repo, build_env)

        return lib_obj


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
                    env['fn_error']("     : %s" % (line))
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


def process_progs(prog_name, env, build_env, all_prog_objs):

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

    progs = {}
    for prog, desc in target_descr_files.items():
        prog_mk_file = desc[1] if desc[0] == 'mk' else None
        prog_mk_repo = desc[2] if desc[0] == 'mk' else None
        prog_sc_file = desc[1] if desc[0] == 'sc' else None
        prog_sc_repo = desc[2] if desc[0] == 'sc' else None

        if prog not in all_prog_objs:
            all_prog_objs[prog] = None
            prog_obj = process_prog(prog,
                                    prog_mk_file, prog_mk_repo,
                                    prog_sc_file, prog_sc_repo,
                                    env, build_env)
            all_prog_objs[prog] = prog_obj
        else:
            prog_obj = all_prog_objs[prog]
            if prog_obj is None:
                env['fn_error']("Circular program dependency detected when processing '%s'"
                                % (prog))
                quit()
            prog_obj.increase_use_count()

        progs[prog] = prog_obj

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
            prog_obj = genode_prog.GenodeMkProg(prog_name, env,
                                                prog_mk_file, prog_mk_repo,
                                                build_env)
            prog_obj.process_load()
        else:
            process_prog_overlay_fun = buildtool_tools.get_process_prog_overlay_fun(overlay_file_path)

            # process load
            prog_obj = process_prog_overlay_fun(prog_name, env, prog_mk_file, prog_mk_repo, build_env)

        return prog_obj


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


def setup_ccache(env, conf_build_env, base_build_env):

    tool_var_path = '%s/var/tool/ccache' % env['BUILD']

    cc = conf_build_env.var_value('CUSTOM_CC')
    cc_dir, cc_name = os.path.split(cc)
    cc_ccache = os.path.join(tool_var_path, cc_name)

    cxx = conf_build_env.var_value('CUSTOM_CXX')
    cxx_dir, cxx_name = os.path.split(cxx)
    cxx_ccache = os.path.join(tool_var_path, cxx_name)

    if cc_dir != cxx_dir:
        env['fn_error']("ccache enabled but the compilers %s and %s "
                        "reside in different directories" % (cxx, cc))
        quit()

    base_build_env.var_set('CUSTOM_CC', cc_ccache)
    base_build_env.var_set('CUSTOM_CXX', cxx_ccache)

    env['ENV']['CCACHE_PATH'] = cxx_dir
    cmd = "mkdir -p %s" % (tool_var_path)
    results = subprocess.run(cmd, stdout=subprocess.PIPE,
                             shell=True, universal_newlines=True, check=True)
    cmd = "ln -sf `command -v ccache` %s" % (cc_ccache)
    results = subprocess.run(cmd, stdout=subprocess.PIPE,
                             shell=True, universal_newlines=True, check=True)
    cmd = "ln -sf `command -v ccache` %s" % (cxx_ccache)
    results = subprocess.run(cmd, stdout=subprocess.PIPE,
                             shell=True, universal_newlines=True, check=True)

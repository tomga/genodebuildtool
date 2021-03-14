
import os

import SCons.Action

def process_mk_overlay(mk_file, build_env):

    env = build_env.scons_env

    include_mk = build_env.get_mk_cache().get_parsed_mk(mk_file, no_overlay=True)
    include_mk.process(build_env)

    # create targets later to get access to PROG_LINK_TARGETS defined
    # during processing of genode_prog

    delayed_action = lambda : create_targets(mk_file, build_env)
    env['fn_add_post_process_action'](delayed_action)


def create_targets(mk_file, build_env):

    env = build_env.scons_env

    ## NOTICE: ignoring LIBCXX_GCC as it is only set in cxx.mk and it
    ## seems that its value cannot get here

    prog_link_items = list(map(str, env['PROG_LINK_ITEMS']))
    env['fn_debug']("%s: %s" % ('PROG_LINK_ITEMS', str(prog_link_items)))

    core_lib_basename = build_env.var_value('CORE_LIB')
    core_lib = env['fn_sc_tgt_path'](core_lib_basename)
    env['fn_debug']("%s: %s" % ('core_lib', str(core_lib)))

    prog_targets = []

    env['ADDLIBPREFIX'] = '\\naddlib '
    env['ADDLIBSUFFIX'] = ''
    env['_ADDLIB'] = '${_concat(ADDLIBPREFIX, ADDLIB, ADDLIBSUFFIX, __env__)}'
    env['__ADDLIB'] = '$_ADDLIB'

    env['ADDLIB'] = list(map(env['fn_unsconsify_path'], map(str, prog_link_items)))

    env['MERGECOM'] = ('(echo "create ${TARGET}"; echo -e "$__ADDLIB";'
                       + ' echo "save"; echo "end"; ) | ${AR} -M')
    core_lib_a = env.Command(
        target=str(core_lib),
        source=prog_link_items,
        action=SCons.Action.Action("$MERGECOM", "$MERGECOMSTR")
    )
    prog_targets.append(core_lib_a)

    # NOTE: ignoring check for INSTALL_DIR and DEBUG_DIR as it seems
    # they are always defined

    # stripped version
    strip_tgt = env.Strip(target=env['fn_sc_tgt_path']('%s.stripped' % (core_lib_basename)),
                          STRIP_OPTIONS='--strip-unneeded',
                          source=core_lib_a)
    prog_targets.append(strip_tgt)

    # symlink to stripped version
    inst_prog_tgt = env.SymLink(source = strip_tgt,
                                target = env['fn_sconsify_path'](os.path.join(env['INSTALL_DIR'],
                                                                              core_lib_basename)))
    prog_targets.append(inst_prog_tgt)


    # symlink to debug version
    dbg_prog_tgt = env.SymLink(source = core_lib_a,
                               target = env['fn_sconsify_path'](os.path.join(env['DEBUG_DIR'],
                                                                             core_lib_basename)))
    prog_targets.append(dbg_prog_tgt)

    env.Alias(env['fn_current_target_alias'](), prog_targets)

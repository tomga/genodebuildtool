
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

    env['LD_MARCH'] = build_env.var_value('LD_MARCH')
    env['fn_debug']("%s: %s" % ('LD_MARCH', env['LD_MARCH']))

    core_obj_basename = build_env.var_value('CORE_OBJ')
    core_obj = env['fn_sc_tgt_path'](core_obj_basename)
    env['fn_debug']("%s: %s" % ('core_obj', str(core_obj)))

    prog_targets = []

    env['MERGECOM'] = "${LD} ${LD_MARCH} -u _start --whole-archive -r ${SOURCES} -o ${TARGET}"
    core_obj_o = env.Command(
        target=str(core_obj),
        source=prog_link_items,
        action=SCons.Action.Action("$MERGECOM", "$MERGECOMSTR")
    )
    prog_targets.append(core_obj_o)

    # NOTE: ignoring check for INSTALL_DIR and DEBUG_DIR as it seems
    # they are always defined

    # stripped version
    strip_tgt = env.Strip(target=env['fn_sc_tgt_path']('%s.stripped' % (core_obj_basename)),
                          STRIP_OPTIONS='--strip-debug',
                          source=core_obj_o)
    prog_targets.append(strip_tgt)

    # symlink to stripped version
    inst_prog_tgt = env.SymLink(source = strip_tgt,
                                target = env['fn_sconsify_path'](os.path.join(env['INSTALL_DIR'],
                                                                              core_obj_basename)))
    prog_targets.append(inst_prog_tgt)


    # symlink to debug version
    dbg_prog_tgt = env.SymLink(source = core_obj_o,
                               target = env['fn_sconsify_path'](os.path.join(env['DEBUG_DIR'],
                                                                             core_obj_basename)))
    prog_targets.append(dbg_prog_tgt)

    env.Alias(env['ent_current_target_alias'], prog_targets)

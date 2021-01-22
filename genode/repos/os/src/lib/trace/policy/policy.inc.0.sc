
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
    tgt = env['fn_current_target_obj']()

    env['CC_MARCH'] = build_env.var_value('CC_MARCH')
    env['CXX_OPT'] = build_env.var_value('CXX_OPT')
    env['SHCXXCOM'] = '$SHCXX -o $TARGET -c $CC_MARCH $CXX_OPT $_CCCOMCOM $SOURCES'

    src_list = ['table.cc', 'policy.cc']
    src_files = tgt.get_sources(src_list)
    env['fn_debug']('sources: %s' % (str(src_files)))
    cc_objs = tgt.build_helper.compile_cc_sources(tgt.env, src_files)
    env['fn_debug']('cc_objs: %s' % (str(src_files)))

    env['LD_SCRIPT'] = env['fn_localize_path'](build_env.var_value('LD_SCRIPT'))
    env['fn_debug']('LD_SCRIPT: %s' % (str(env['LD_SCRIPT'])))
    env['fn_debug']('LD_LIBGCC: %s' % (env['LD_LIBGCC']))
    env['LD_MARCH'] = build_env.var_value('LD_MARCH')
    env['fn_debug']("%s: %s" % ('LD_MARCH', env['LD_MARCH']))

    target_policy_basename = build_env.var_value('TARGET_POLICY')
    target_policy = env['fn_sc_tgt_path'](target_policy_basename + '.elf')
    env['fn_debug']("%s: %s" % ('target_policy', str(target_policy)))

    prog_targets = []

    env['LINKCOM'] = "${LD} ${LD_MARCH} -T ${LD_SCRIPT} -Ttext=0 ${SOURCES} ${LD_LIBGCC} -o ${TARGET}"
    target_policy_elf = env.Command(
        target=str(target_policy),
        source=cc_objs,
        action=SCons.Action.Action("$LINKCOM", "$LINKCOMSTR")
    )
    env.Depends(target_policy_elf, env['LD_SCRIPT'])
    prog_targets.append(target_policy_elf)


    env['OBJCPYCOM'] = "${OBJCOPY} -O binary ${SOURCES} ${TARGET}"
    policy_inst = env.Command(
        target = env['fn_sconsify_path'](os.path.join(env['INSTALL_DIR'],
                                                      target_policy_basename)),
        source=target_policy_elf,
        action=SCons.Action.Action("$OBJCPYCOM", "$OBJCPYCOMSTR")
    )
    prog_targets.append(policy_inst)


    env.Alias(env['fn_current_target_alias'](), prog_targets)

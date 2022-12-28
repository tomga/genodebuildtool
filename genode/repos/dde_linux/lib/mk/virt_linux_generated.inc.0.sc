
def process_mk_overlay(mk_file, build_env):

    env = build_env.scons_env

    include_mk = build_env.get_mk_cache().get_parsed_mk(mk_file, forced_overlay_type='no_overlay')
    include_mk.process(build_env)

    # create targets later to get access to variables defined later
    delayed_action = lambda : create_targets(mk_file, build_env)
    env['fn_add_post_process_action'](delayed_action)


def create_targets(mk_file, build_env):

    env = build_env.scons_env

    sc_tgt_file = env['fn_norm_tgt_path']('kernel_config.tag')
    lx_dir = env['fn_localize_path'](build_env.var_value('LX_DIR'))

    conf_tgt = env.LinuxKTag(target = sc_tgt_file,
                             lx_dir = lx_dir,
                             lx_mk_args = build_env.var_value('LX_MK_ARGS'),
                             lx_enable = build_env.var_values('LX_ENABLE'),
                             lx_disable = build_env.var_values('LX_DISABLE'),
                             )

    env.Alias(env['ent_current_target_alias'], [conf_tgt])

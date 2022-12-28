
import SCons.Action

def process_mk_overlay(mk_file, build_env):

    env = build_env.scons_env

    include_mk = build_env.get_mk_cache().get_parsed_mk(mk_file, forced_overlay_type='.patch')
    include_mk.process(build_env)

    def target_opts_modifier(src, opts):
        src = 'wireguard'
        return opts + [ f'-DKBUILD_MODFILE=\'"{src}"\'',
                        f'-DKBUILD_BASENAME=\'"{src}"\'',
                        f'-DKBUILD_MODNAME=\'"{src}"\'',
                       ]

    env['fn_register_modify_target_opts'](env, 'drivers/net/wireguard/device.c', target_opts_modifier, priority=10)
    env['fn_register_modify_target_opts'](env, 'drivers/net/wireguard/netlink.c', target_opts_modifier, priority=10)

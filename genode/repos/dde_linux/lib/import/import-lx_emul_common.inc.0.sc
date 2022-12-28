
import os

import SCons.Action

def process_mk_overlay(mk_file, build_env):

    env = build_env.scons_env

    include_mk = build_env.get_mk_cache().get_parsed_mk(mk_file, forced_overlay_type='.patch')
    include_mk.process(build_env)

    lx_src = build_env.var_values('LX_SRC')
    env['fn_debug'](f'LX_SRC: {str(lx_src)}')

    def target_opts_modifier(src, opts):
        src = src[:-2] if src[-2:] == '.c' else src
        src_basename = os.path.basename(src)
        return opts + [ f'-DKBUILD_MODFILE=\'"{src}"\'',
                        f'-DKBUILD_BASENAME=\'"{src_basename}"\'',
                        f'-DKBUILD_MODNAME=\'"{src_basename}"\'',
                       ]

    for src in lx_src:
        env['fn_register_modify_target_opts'](env, src, target_opts_modifier)

    env['fn_register_modify_target_opts'](env, 'generated_dummies.c', target_opts_modifier)
    env['fn_register_modify_target_opts'](env, 'dummies.c', target_opts_modifier)

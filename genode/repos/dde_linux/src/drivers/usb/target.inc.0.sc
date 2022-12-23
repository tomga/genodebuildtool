
import SCons.Action

def process_mk_overlay(mk_file, build_env):

    env = build_env.scons_env

    cc_cxx_opt = build_env.var_value('CC_CXX_OPT')

    include_mk = build_env.get_mk_cache().get_parsed_mk(mk_file, forced_overlay_type='no_overlay')
    include_mk.process(build_env)

    cc_cxx_opt = build_env.var_set('CC_CXX_OPT', cc_cxx_opt + ' -fpermissive')

    def target_opts_modifier(opts):
        return [ o if o != '-DMOD_SUFFIX=' else o + '"_core"' for o in opts ]

    env['fn_register_modify_target_opts'](env, 'hid/hid-core.c', target_opts_modifier)

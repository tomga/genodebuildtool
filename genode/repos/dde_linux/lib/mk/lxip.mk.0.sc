
from gscons import genode_lib
import gscons.utils

class GenodeLxipMkLib(genode_lib.GenodeMkLib):

    def get_c_sources(self):
        src_c = self.build_env.var_values('SRC_C')
        src_c = gscons.utils.nodups(src_c) # fix for duplicated net/ipv4/ipconfig.c
        return self.get_sources(src_c)


    def build_c_objects(self):

        def target_opts_modifier(src, opts):
            return [ o if o != '-DSETUP_SUFFIX=' else o + '"_eth"' for o in opts ]

        self.env['fn_register_modify_target_opts'](self.env, 'net/ethernet/eth.c',
                                                   target_opts_modifier)

        return super().build_c_objects()


def process_lib_overlay(lib_name, env, lib_mk_file, lib_mk_repo, build_env):
    lib = GenodeLxipMkLib(lib_name, env, lib_mk_file, lib_mk_repo, build_env)
    lib.disable_overlay()
    lib.process_load()
    return lib

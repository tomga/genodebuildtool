
import os

from gscons import genode_lib

class GenodeDdeLinuxLxEmulMkLib(genode_lib.GenodeMkLib):

    def __init__(self, lib_name, env, lib_mk_file, lib_mk_repo, build_env,
                 symlink_print_flags=None):
        self.symlink_print_flags = symlink_print_flags
        super().__init__(lib_name, env, lib_mk_file, lib_mk_repo, build_env)


    def process_load(self):
        retval = super().process_load()

        build_env = self.build_env

        # important to create this directory here because if it does not exist
        # early it is not used as include path
        gen_inc_dir = build_env.var_value('GEN_INC')
        if not os.path.isdir(gen_inc_dir):
            os.makedirs(gen_inc_dir)

        return retval


    def process_target(self):

        env = self.env.Clone()
        build_env = self.build_env

        lx_emul_h = build_env.var_value('LX_EMUL_H')
        gen_inclues = build_env.var_values('GEN_INCLUDES')

        # MK_COMPATIBILITY: for exact output compatibility with make
        if self.symlink_print_flags is not None:
            env['SYMLINK_PRINT_FLAGS'] = self.symlink_print_flags

        include_targets = []
        for include_h in gen_inclues:
            include_lnk_tgt = env.SymLink(source = lx_emul_h,
                                          target = env['fn_localize_path'](include_h))
            include_targets.extend(include_lnk_tgt)

        # MK_COMPATIBILITY: without the line below only required
        # include links are created and that is incompatible with make
        env.Alias(env['fn_lib_alias_name'](self.lib_name), include_targets)

        retval = super().process_target()

        return retval

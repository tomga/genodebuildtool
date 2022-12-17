
from gscons import genode_lib
import SCons.Action

class GenodeLibnlIncludeMkLib(genode_lib.GenodeMkLib):

    def do_process_target(self):

        super().do_process_target()

        env = self.env
        build_env = self.build_env

        emul_includes = build_env.var_values('EMUL_INCLUDES')
        libnl_emul_h = build_env.var_value('LIBNL_EMUL_H')

        sc_emul_includes = list(map(lambda x: env['fn_sconsify_path'](x), emul_includes))
        sc_libnl_emul_h = env['fn_sconsify_path'](libnl_emul_h)

        targets = []
        for i in sc_emul_includes:
            tgt = env.SymLink(target=i,
                              source=sc_libnl_emul_h,
															SYMLINK_PRINT_FLAGS='-s')
            targets.append(tgt)

        return env.Alias(env['ent_current_target_alias'], targets)


def process_lib_overlay(lib_name, env, lib_mk_file, lib_mk_repo, build_env):
    env['fn_debug']("process_lib_overlay start")
    lib = GenodeLibnlIncludeMkLib(lib_name, env, lib_mk_file, lib_mk_repo, build_env)
    lib.disable_overlay()
    lib.process_load()
    env['fn_debug']("process_lib_overlay end")
    return lib

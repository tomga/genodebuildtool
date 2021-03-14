
import os

from gscons import genode_lib
import gscons.utils

class GenodeIwlFirmwareMkLib(genode_lib.GenodeMkLib):

    def process_target(self):

        super().process_target()

        env = self.env
        build_env = self.build_env

        fw_dir = build_env.var_value('FW_DIR')
        bin_dir = build_env.var_value('BIN_DIR')

        images = build_env.var_values('IMAGES')
        env['fn_debug']("%s: %s" % ('IMAGES', str(images)))

        targets = []
        for i in images:
            tgt = env.Copy(target=os.path.join(bin_dir, i),
                           source=os.path.join(fw_dir, i))
            targets.append(tgt)

        return env.Alias(env['fn_current_target_alias'](), targets)


def process_lib_overlay(lib_name, env, lib_mk_file, lib_mk_repo, build_env):
    lib = GenodeIwlFirmwareMkLib(lib_name, env, lib_mk_file, lib_mk_repo, build_env)
    lib.disable_overlay()
    lib.process_load()
    return lib

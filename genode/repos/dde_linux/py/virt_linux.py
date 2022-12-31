
import os
from gscons import genode_prog
import SCons.Action


class GenodeDdeLinuxVirtMkProg(genode_prog.GenodeMkProg):

    def do_process_target(self):

        super().do_process_target()

        env = self.env
        build_env = self.build_env

        sc_tgt_file = env['fn_norm_tgt_path']('kernel_config.tag')
        lx_dir = env['fn_localize_path'](build_env.var_value('LX_DIR'))

        conf_tgt = env.LinuxKTag(target = sc_tgt_file,
                                 lx_dir = lx_dir,
                                 lx_mk_args = build_env.var_value('LX_MK_ARGS'),
                                 lx_enable = build_env.var_values('LX_ENABLE'),
                                 lx_disable = build_env.var_values('LX_DISABLE'),
                                 )

        bzimage_tgt = env.LinuxBzImage(source = conf_tgt,
                                       lx_dir = lx_dir,
                                       lx_mk_args = build_env.var_value('LX_MK_ARGS'),
                                       )

        return env.Alias(env['ent_current_target_alias'], [conf_tgt, bzimage_tgt])


import os
from gscons import genode_prog
import SCons.Action


class GenodeDdeLinuxVirtMkProg(genode_prog.GenodeMkProg):

    def __init__(self, prog_name, env,
                 prog_mk_file, prog_mk_repo,
                 build_env,
                 lx_target):
        super().__init__(prog_name, env,
                         prog_mk_file, prog_mk_repo,
                         build_env)
        self.lx_target = lx_target


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

        bzimage_tgt = env.LinuxBuild(source = conf_tgt,
                                     lx_dir = lx_dir,
                                     lx_mk_args = build_env.var_value('LX_MK_ARGS'),
                                     lx_target = self.lx_target,
                                     )

        return env.Alias(env['ent_current_target_alias'], [conf_tgt, bzimage_tgt])

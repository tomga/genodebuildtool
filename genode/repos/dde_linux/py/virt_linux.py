
import os
from gscons import genode_prog
import SCons.Action


class GenodeDdeLinuxVirtMkProg(genode_prog.GenodeMkProg):

    def __init__(self, prog_name, env,
                 prog_mk_file, prog_mk_repo,
                 build_env,
                 lx_target, lx_ktag_without_prepare = False):
        super().__init__(prog_name, env,
                         prog_mk_file, prog_mk_repo,
                         build_env)
        self.lx_target = lx_target
        self.lx_ktag_without_prepare = lx_ktag_without_prepare


    def do_process_target(self):

        super().do_process_target()

        env = self.env
        build_env = self.build_env

        sc_tgt_file = env['fn_norm_tgt_path']('kernel_config.tag')
        lx_dir = env['fn_localize_path'](build_env.var_value('LX_DIR'))

        def update_lx_mk_args(lx_mk_args):
            """If CC is set in args and relative path points to build directory
               then it has to be replaced to absolute for linux build"""
            build_dir = env['BUILD']
            abs_build_dir = os.path.abspath(build_dir)
            rel_cc_prefix = 'CC=%s' % build_dir
            abs_cc_prefix = 'CC=%s' % abs_build_dir
            return lx_mk_args.replace(rel_cc_prefix, abs_cc_prefix)

        lx_mk_args = build_env.var_value('LX_MK_ARGS')
        lx_mk_args = update_lx_mk_args(lx_mk_args)

        conf_tgt = env.LinuxKTag(target = sc_tgt_file,
                                 lx_dir = lx_dir,
                                 lx_mk_args = lx_mk_args,
                                 lx_enable = build_env.var_values('LX_ENABLE'),
                                 lx_disable = build_env.var_values('LX_DISABLE'),
                                 without_prepare = self.lx_ktag_without_prepare,
                                 )

        bzimage_tgt = env.LinuxBuild(source = conf_tgt,
                                     lx_dir = lx_dir,
                                     lx_mk_args = lx_mk_args,
                                     lx_target = self.lx_target,
                                     )

        return env.Alias(env['ent_current_target_alias'], [conf_tgt, bzimage_tgt])

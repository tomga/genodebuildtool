
import os

import SCons.Action

from gscons import genode_lib
import gscons.utils

class GenodeWireguardLxIncDirsMkLib(genode_lib.GenodeMkLib):

    def do_process_target(self):

        env = self.env
        build_env = self.build_env

        # register target for vpath processing before processing
        # original makefile
        tgt_dir = 'arch/x86/crypto'
        tgt_file = 'poly1305-x86_64-cryptogams.S'
        sc_tgt_dir = env['fn_norm_tgt_path'](tgt_dir)
        sc_tgt_file = "%s/%s" % (sc_tgt_dir, tgt_file)
        build_env.register_target_file(sc_tgt_file)
        env['fn_debug']('perl sc_tgt_file: %s' % (sc_tgt_file))

        super().do_process_target()

        lx_src_dir = build_env.var_value('LX_SRC_DIR')
        sc_lx_src_dir = env['fn_localize_path'](lx_src_dir)
        perl_script = 'arch/x86/crypto/poly1305-x86_64-cryptogams.pl'
        sc_perl_script = '%s/%s' % (sc_lx_src_dir, perl_script)

        perl_cmd = r'perl %s > %s' % (sc_perl_script, sc_tgt_file)
        env['fn_debug']('perl_cmd: %s' % perl_cmd)
        perl_tgt = env.Command(
            target=sc_tgt_file,
            source=sc_perl_script,
            action=SCons.Action.Action(perl_cmd,
                                       env['fn_fmt_out'](sc_tgt_file, 'CONVERT', perl_cmd)))

        targets = [perl_tgt]

        return env.Alias(env['ent_current_target_alias'], targets)


def process_lib_overlay(lib_name, env, lib_mk_file, lib_mk_repo, build_env):
    lib = GenodeWireguardLxIncDirsMkLib(lib_name, env, lib_mk_file, lib_mk_repo, build_env)
    lib.disable_overlay()
    lib.process_load()
    return lib

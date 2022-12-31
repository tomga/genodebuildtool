
import os

import SCons.Action

from gscons import genode_lib
import gscons.utils

class GenodeWireguardLxIncDirsMkLib(genode_lib.GenodeMkLib):

    def do_process_target(self):

        env = self.env
        build_env = self.build_env

        base_name = 'poly1305-core'
        perl_base_name = 'poly1305-armv8'
        lx_arch = 'arm64'

        def target_opts_modifier(src, opts):
            retval = opts + ['-Dpoly1305_init=poly1305_init_arm64']
            return retval

        self.env['fn_register_modify_target_opts'](self.env, 'arch/arm64/crypto/poly1305-core.S',
                                                   target_opts_modifier)

        # register target for vpath processing before processing
        # original makefile
        tgt_dir = 'arch/%s/crypto' % (lx_arch)
        tgt_file = '%s.S' % (base_name)
        sc_tgt_dir = env['fn_norm_tgt_path'](tgt_dir)
        sc_tgt_file = "%s/%s" % (sc_tgt_dir, tgt_file)
        build_env.register_target_file(sc_tgt_file)

        super().do_process_target()

        lx_src_dir = build_env.var_value('LX_SRC_DIR')
        sc_lx_src_dir = env['fn_localize_path'](lx_src_dir)
        perl_script = 'arch/%s/crypto/%s.pl' % (lx_arch, perl_base_name)
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
    lib.enforce_overlay_type('.patch')
    lib.process_load()
    return lib

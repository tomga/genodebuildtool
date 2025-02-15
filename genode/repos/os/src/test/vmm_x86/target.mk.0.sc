
import os
from gscons import genode_prog
import SCons.Action


class GenodeTestVmm_x86MkProg(genode_prog.GenodeMkProg):

    def do_process_target(self):

        env = self.env
        build_env = self.build_env

        prog_targets = []

        src_file = env['ent_current_target_obj'].get_sources(['guest.s'])
        src_file = [ os.path.join(d, f) for d, f in src_file ]
        obj_file = [env['fn_sc_tgt_path']('guest.o')]
        bin_file = env['fn_norm_tgt_path']('guest.bin')

        build_env.register_target_file(bin_file)

        super().do_process_target()

        env['BUILDCOM'] = "${CC} -m16 -c ${SOURCES} -o ${TARGET}"
        guest_obj_tgt = env.Command(
            target=obj_file,
            source=src_file,
            action=SCons.Action.Action("$BUILDCOM", "$BUILDCOMSTR")
        )

        env['OBJCPYCOM'] = "${OBJCOPY} -O binary ${SOURCES} ${TARGET}"
        guest_bin_tgt = env.Command(
            target = env['fn_sconsify_path'](bin_file),
            source = guest_obj_tgt,
            action = SCons.Action.Action("$OBJCPYCOM", "$OBJCPYCOMSTR")
        )
        prog_targets.append(guest_bin_tgt)

        return env.Alias(env['ent_current_target_alias'], prog_targets)


def process_prog_overlay(prog_name, env, prog_mk_file, prog_mk_repo, build_env):

    prog = GenodeTestVmm_x86MkProg(prog_name, env, prog_mk_file, prog_mk_repo, build_env)
    prog.disable_overlay()
    prog.process_load(skip_rules=True)

    return prog


from genode.repos.dde_linux.py.virt_linux import GenodeDdeLinuxVirtMkProg

def process_prog_overlay(prog_name, env, prog_mk_file, prog_mk_repo, build_env):

    prog = GenodeDdeLinuxVirtMkProg(prog_name, env, prog_mk_file, prog_mk_repo,
                                    build_env, lx_target = 'bzImage',
                                    lx_ktag_without_prepare = True)
    prog.disable_overlay()
    prog.process_load(skip_rules=True)

    return prog

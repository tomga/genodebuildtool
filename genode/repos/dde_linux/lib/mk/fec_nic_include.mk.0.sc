
from genode.repos.dde_linux.py.lx_emul import GenodeDdeLinuxLxEmulMkLib

def process_lib_overlay(lib_name, env, lib_mk_file, lib_mk_repo, build_env):
    lib = GenodeDdeLinuxLxEmulMkLib(lib_name, env, lib_mk_file, lib_mk_repo, build_env)
    lib.disable_overlay()
    lib.process_load()
    return lib

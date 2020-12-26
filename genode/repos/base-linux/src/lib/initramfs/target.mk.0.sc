
import os
import genode_prog
import SCons.Action

def process_prog_overlay(prog_name, env, prog_mk_file, prog_mk_repo, build_env):

    prog = genode_prog.GenodeMkProg(prog_name, env, prog_mk_file, prog_mk_repo, build_env)
    prog.disable_overlay()
    retval = prog.process()

    env = prog.env
    build_env = prog.build_env

    prog_targets = []

    cc_march = build_env.var_value('CC_MARCH')

    src_c = build_env.var_values('INITRAMFS_SRC_C')
    src_files = [os.path.join(basedir, relpath) for basedir, relpath in prog.get_sources(src_c)]
    src_files = [env['fn_sconsify_path'](path) for path in src_files]

    initramfs_basename = build_env.var_value('INITRAMFS')
    initramfs = env['fn_target_path'](initramfs_basename)

    env['BUILDCOM'] = ("gcc ${SOURCES} -O0 %s  -Wall -W -Wextra -Werror -std=gnu99"
                       + " -o ${TARGET} -Wl,-O3 -Wl,--as-needed -static") % (cc_march)
    initramfs_tgt = env.Command(
        target=str(initramfs),
        source=src_files,
        action=SCons.Action.Action("$BUILDCOM", "$BUILDCOMSTR")
    )
    prog_targets.append(initramfs_tgt)

    # symlink to stripped version
    inst_initramfs_tgt = env.SymLink(source = initramfs_tgt,
                                     target = env['fn_sconsify_path'](os.path.join(env['INSTALL_DIR'],
                                                                                   initramfs_basename)))
    prog_targets.append(inst_initramfs_tgt)

    env.Alias(env['fn_current_target_alias'](), prog_targets)

    return retval

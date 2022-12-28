
import os
import re

import SCons.Action


def linux_kernel_tag(env, target,
                     lx_dir, lx_mk_args, lx_enable, lx_disable,
                     without_prepare = False):

    lx_arch = 'x86'

    sc_tgt_file = target
    norm_tgt_file = env['fn_norm_tgt_path']('Linux')
    sc_conf_script = env['fn_sconsify_path'](lx_dir + '/scripts/config')

    # generated targets, temporarily listed here
    generated = ['include/generated/autoconf.h',
                 'include/generated/timeconst.h',
                 'include/generated/utsrelease.h',
                 'include/generated/bounds.h',
                 'include/generated/uapi/linux/version.h',
                 'include/generated/asm-offsets.h',
                 'arch/{arch}/include/generated/asm/module.lds.h',
                 'arch/{arch}/include/generated/asm/mcs_spinlock.h',
                 'arch/{arch}/include/generated/asm/export.h',
                 'arch/{arch}/include/generated/asm/syscalls_32.h',
                 'arch/{arch}/include/generated/asm/unaligned.h',
                 'arch/{arch}/include/generated/asm/mmiowb.h',
                 'arch/{arch}/include/generated/asm/syscalls_64.h',
                 'arch/{arch}/include/generated/asm/kmap_size.h',
                 'arch/{arch}/include/generated/asm/unistd_32_ia32.h',
                 'arch/{arch}/include/generated/asm/local64.h',
                 'arch/{arch}/include/generated/asm/unistd_64_x32.h',
                 'arch/{arch}/include/generated/asm/irq_regs.h',
                 'arch/{arch}/include/generated/asm/rwonce.h',
                 'arch/{arch}/include/generated/asm/early_ioremap.h',
                 'arch/{arch}/include/generated/uapi/asm/socket.h',
                 'arch/{arch}/include/generated/uapi/asm/unistd_32.h',
                 'arch/{arch}/include/generated/uapi/asm/errno.h',
                 'arch/{arch}/include/generated/uapi/asm/types.h',
                 'arch/{arch}/include/generated/uapi/asm/poll.h',
                 'arch/{arch}/include/generated/uapi/asm/termbits.h',
                 'arch/{arch}/include/generated/uapi/asm/termios.h',
                 'arch/{arch}/include/generated/uapi/asm/sockios.h',
                 'arch/{arch}/include/generated/uapi/asm/unistd_x32.h',
                 'arch/{arch}/include/generated/uapi/asm/resource.h',
                 'arch/{arch}/include/generated/uapi/asm/fcntl.h',
                 'arch/{arch}/include/generated/uapi/asm/unistd_64.h',
                 'arch/{arch}/include/generated/uapi/asm/param.h',
                 'arch/{arch}/include/generated/uapi/asm/bpf_perf_event.h',
                 'arch/{arch}/include/generated/uapi/asm/ioctls.h',
                 'arch/{arch}/include/generated/uapi/asm/ipcbuf.h',
                 'arch/{arch}/include/generated/uapi/asm/ioctl.h',
                 ]
    sc_generated = [ env['fn_norm_tgt_path'](x.format(arch=lx_arch)) for x in generated ]

    conf_cmd = ['$MAKE -C $LX_DIR O=$LX_PWD $LX_MK_ARGS tinyconfig $BUILD_OUTPUT_FILTER',
                '$LX_DIR/scripts/config --file $PWD/.config $LX_ENABLE_ARGS',
                '$LX_DIR/scripts/config --file $PWD/.config $LX_DISABLE_ARGS',
                '$MAKE -C $PWD $LX_MK_ARGS olddefconfig $BUILD_OUTPUT_FILTER',
                '$MAKE -C $PWD $LX_MK_ARGS prepare      $BUILD_OUTPUT_FILTER',
                'touch $TAG_TARGET',
                ]
    if without_prepare:
        conf_cmd.pop(-2)

    env['fn_debug']('conf_cmd: %s' % conf_cmd)
    conf_tgt = env.Command(
        target=[sc_tgt_file] + sc_generated,
        source=sc_conf_script,
        action=SCons.Action.Action(conf_cmd,
                                   env['fn_fmt_out'](norm_tgt_file, 'CONFIG', conf_cmd)),
        LX_DIR = lx_dir,
        PWD = env['fn_norm_tgt_path'](None),
        LX_PWD = os.path.relpath(env['fn_norm_tgt_path'](None), lx_dir),
        LX_MK_ARGS = lx_mk_args,
        LX_ENABLE_ARGS = ' '.join(['--enable ' + x for x in lx_enable]),
        LX_DISABLE_ARGS = ' '.join(['--disable ' + x for x in lx_disable]),
        TAG_TARGET = sc_tgt_file,
        BUILD_OUTPUT_FILTER = '2>&1 | sed "`echo s/^/______[Linux]__/ | %s`"' % ("tr '_' ' '"),
    )

    return conf_tgt


def exists(env):
    return True


def generate(env):
    '''
    env.LinuxKTag(env, target,
                  lx_dir, lx_mk_args, lx_enable, lx_disabletarget,
                  without_prepare=False)
    '''

    env.AddMethod(linux_kernel_tag, "LinuxKTag")


import os
import re

import SCons.Action


def linux_build(env, source,
                lx_dir, lx_mk_args, lx_target):

    sc_tgt_file = env['fn_norm_tgt_path']('linux_build.tag')
    norm_tgt_file = env['fn_norm_tgt_path']('Linux')

    if lx_target is None:
        lx_target = ''
    conf_cmd = ['$MAKE -C $PWD $LX_MK_ARGS %s $BUILD_OUTPUT_FILTER' % (lx_target),
                'touch %s' % (sc_tgt_file),
                ]

    build_tgt = env.Command(
        target=[sc_tgt_file],
        source=source,
        action=SCons.Action.Action(conf_cmd,
                                   env['fn_fmt_out'](norm_tgt_file, 'BUILD', conf_cmd)),
        LX_DIR = lx_dir,
        PWD = env['fn_norm_tgt_path'](None),
        LX_MK_ARGS = lx_mk_args,
        BUILD_OUTPUT_FILTER = '2>&1 | sed "`echo s/^/______[Linux]__/ | %s`"' % ("tr '_' ' '"),
    )

    return build_tgt


def exists(env):
    return True


def generate(env):
    '''
    env.LinuxBzImage(env, source,
                     lx_dir, lx_mk_args)
    '''

    env.AddMethod(linux_build, "LinuxBuild")

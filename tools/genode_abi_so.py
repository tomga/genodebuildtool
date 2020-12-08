
import os
import re

from SCons.Node import FS
from SCons.Script import Action, Builder
from SCons.Action import CommandGeneratorAction

def generate(env):
    '''
    AbiSo(abi_so, symbols_obj)
    env.AbiSo(abi_so, symbols_obj)

    Generates %.abi.so file from %.symbols.o
    '''
    bldr = Builder(action = CommandGeneratorAction(generator = abi_so_generator,
                                                   kw = {'strfunction': abi_so_print}),
                   emitter = abi_so_emitter,
                   suffix = '.symbols.s',
                   src_suffixes = '.symbols')
    env.Append(BUILDERS = {'LibAbiSo' : bldr})


def exists(env):
    return True

def process_T_options(ld_opts, env):

    scripts = []

    def scripts_normalize(match):
        match = match.group()
        script = match[2:].strip()
        script = env['fn_localize_path'](script)
        scripts.append(script)
        return '-T ' + script

    ld_opts = ' '.join(ld_opts.split())
    ld_opts = re.sub(r'-T *[^ ]+', scripts_normalize, ld_opts)

    return ld_opts, scripts


def abi_so_emitter(target, source, env):

    main_script = env['fn_localize_path'](env['LD_SCRIPT_SO'])
    ld_opts, scripts = process_T_options(env['LD_OPT'], env)
    env['fn_debug']('abi_so_emitter: %s %s' % (str(target), str(source + [main_script] + scripts)))
    return (target, source + [main_script] + scripts)


def abi_so_generator(target, source, env, for_signature):

    ld_opts, scripts = process_T_options(env['LD_OPT'], env)

    d = { 'ld': env['LD'],
          'abi_so': target[0],
          'abi_soname': os.path.basename(str(target[0]))[0:-len('.abi.so')] + '.lib.so',
          'ld_opts': ld_opts,
          'ld_script_so': source[1],
          'lib_so_deps': env['LIB_SO_DEPS'],
          'symbols_obj': source[0],
          }

    cmd = r"""{ld} -o {abi_so} -soname={abi_soname} -shared --eh-frame-hdr {ld_opts}
                   -T {ld_script_so}
                   --whole-archive --start-group
                   {lib_so_deps} {symbols_obj}
                   --end-group --no-whole-archive
    """

    cmd = cmd.format(**d)
    cmd = cmd.replace('\n', ' ')
    cmd = ' '.join(cmd.split())

    return cmd


def abi_so_print(target, source, env, executor=None):
    presentation = target[0]
    if 'fn_prettify_path' in env:
        presentation = env['fn_prettify_path'](presentation)
    retval = ' MERGE    %s' % (presentation)
    if env['VERBOSE_OUTPUT']:
        retval += '\n%s' % (abi_so_generator(target, source, env, True))
    return retval


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
    return process_file_options(ld_opts, env, '-T', ' ')

def process_version_script_options(ld_opts, env):
    return process_file_options(ld_opts, env, '--version-script=', '')

def process_file_options(ld_opts, env, option, optsep):
    scripts = []
    def scripts_normalize(match):
        match = match.group()
        script = match[len(option):].strip()
        if script.startswith('/'):
            script = env['fn_localize_path'](script)
        else:
            script = env['fn_norm_tgt_path'](script)
        scripts.append(script)
        return option + optsep + script

    ld_opts = ' '.join(ld_opts.split())
    ld_opts = re.sub(option + r' *[^ ]+', scripts_normalize, ld_opts)

    return ld_opts, scripts


def abi_so_emitter(target, source, env):

    ld_script_so = env['fn_localize_path'](env['LD_SCRIPT_SO']).split()
    main_script = ld_script_so[0]
    hidden_opts, hidden_scripts = process_T_options(' '.join(ld_script_so[1:]), env)

    ld_opts = env['LD_OPT']
    ld_opts, scripts = process_T_options(ld_opts, env)
    ld_opts, vscripts = process_version_script_options(ld_opts, env)

    env['fn_debug']('abi_so_emitter: %s %s' %
                    (str(list(map(str, target))),
                     str(list(map(str, source + [main_script] + hidden_scripts + scripts + vscripts)))))
    return (target, source + [main_script] + hidden_scripts + scripts + vscripts)


def abi_so_generator(target, source, env, for_signature):

    ld_script_so = env['fn_localize_path'](env['LD_SCRIPT_SO']).split()
    main_script = ld_script_so[0]
    hidden_opts, hidden_scripts = process_T_options(' '.join(ld_script_so[1:]), env)

    ld_opts = env['LD_OPT']
    ld_opts, scripts = process_T_options(ld_opts, env)
    ld_opts, vscripts = process_version_script_options(ld_opts, env)

    emitter_added_src_count = len(hidden_scripts) + len(scripts) + len(vscripts) + 1

    d = { 'ld': env['LD'],
          'abi_so': target[0],
          'abi_soname': os.path.basename(str(target[0]))[0:-len('.abi.so')] + '.lib.so',
          'ld_opts': ld_opts,
          'ld_script_so': main_script,
          'ld_script_rest': hidden_opts,
          'lib_so_deps': env['LIB_SO_DEPS'],
          'symbols_obj': source[0],
          }

    cmd = r"""{ld} -o {abi_so} -soname={abi_soname} -shared --eh-frame-hdr {ld_opts}
                   -T {ld_script_so} {ld_script_rest}
                   {lib_so_deps} {symbols_obj}
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


import os

from SCons.Node import FS
from SCons.Script import Action, Builder
from SCons.Action import CommandGeneratorAction

def generate(env):
    '''
    Symbols(asm_source, symbols_file)
    env.Symbols(asm_source, symbols_file)

    Generates %.symbols.s file from %.symbols
    '''
    bldr = Builder(action = CommandGeneratorAction(generator = symbols_generator,
                                                   kw = {'strfunction': symbols_print}),
                   suffix = '.symbols.s',
                   src_suffixes = '.symbols')
    env.Append(BUILDERS = {'Symbols' : bldr})


def exists(env):
    return True


def symbols_generator(target, source, env, for_signature):

    ## TODO: check if SPECS change cause rebuild; probably it should
    ## as command is treated as a dependency
    if 'x86_64' in env['SPECS']:
        asm_sym_dependency = r'movq \1@GOTPCREL(%rip), %rax'
    else:
        asm_sym_dependency = r'.long \1'

    cmd = r"""sed -e "s/^\(\w\+\) D \(\w\+\)\$/.data; .global \1; .type \1,%object; .size \1,\2; \1: .skip 1/"
                  -e "s/^\(\w\+\) V/.data; .weak \1; .type \1,%object; \1: .skip 1/"
                  -e "s/^\(\w\+\) T/.text; .global \1; .type \1,%function; \1:/"
                  -e "s/^\(\w\+\) R \(\w\+\)\$/.section .rodata; .global \1; .type \1,%object; .size \1,\2; \1:/"
                  -e "s/^\(\w\+\) W/.text; .weak \1; .type \1,%function; \1:/"
                  -e "s/^\(\w\+\) B \(\w\+\)\$/.bss; .global \1; .type \1,%object; .size \1,\2; \1:/"
    """
    cmd += r' -e "s/^\(\w\+\) U/.text; .global \1; %s/"' % (asm_sym_dependency)
    cmd += '  %s > %s' % (source[0], target[0])

    cmd = cmd.replace('\n', ' ')
    cmd = ' '.join(cmd.split())

    return cmd

def symbols_print(target, source, env):
    presentation = target[0]
    if 'fn_prettify_path' in env:
        presentation = env['fn_prettify_path'](presentation)
    retval = ' CONVERT  %s' % (presentation)
    if env['VERBOSE_OUTPUT']:
        retval += '\n%s' % (symbols_generator(target, source, env, True))
    return retval

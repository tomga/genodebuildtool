
import os

from SCons.Node import FS
from SCons.Script import Action, Builder
from SCons.Action import CommandGeneratorAction

def generate(env):
    '''
    BinaryObj(binary_source, binary_file)
    env.BinaryObj(binary_source, binary_file)

    Generates %.binary.s file from %.binary
    '''
    bldr = Builder(action = CommandGeneratorAction(generator = binary_generator,
                                                   kw = {'strfunction': binary_print}),
                   prefix = 'binary_',
                   suffix = '.o')
    env.Append(BUILDERS = {'BinaryObj' : bldr})


def exists(env):
    return True


def binary_generator(target, source, env, for_signature):

    symbol_name = '_binary_%s' % (os.path.basename(str(source[0])).replace('.', '_').replace('-', '_'))

    cmd = (r'echo ".global %s_start, %s_end; .data; .align 4; %s_start:; .incbin \"%s\"; %s_end:" | '
           % (symbol_name, symbol_name, symbol_name, source[0], symbol_name))

    cmd += r'%s %s -f -o %s -' % (env['AS'], env['AS_OPT'], target[0])

    cmd = ' '.join(cmd.split())

    return cmd

def binary_print(target, source, env):
    presentation = target[0]
    if 'fn_prettify_path' in env:
        presentation = env['fn_prettify_path'](presentation)
    retval = ' CONVERT  %s' % (presentation)
    if env['VERBOSE_OUTPUT']:
        retval += '\n%s' % (binary_generator(target, source, env, True))
    return retval


import os
import re

from SCons.Node import FS
from SCons.Script import Action, Builder
from SCons.Action import CommandGeneratorAction

def generate(env):
    '''
    DebugSymbols(target, source)
    env.DebugSymbols(target, source)

    Copies debug symbols from source to target
    '''
    bldr = Builder(action = CommandGeneratorAction(generator = debugsymbols_generator,
                                                   kw = {'strfunction': debugsymbols_print}))
    env.Append(BUILDERS = {'DebugSymbols' : bldr})


def exists(env):
    return True


def debugsymbols_generator(target, source, env, for_signature):

    d = { 'objcopy': env['OBJCOPY'],
          'target': target[0],
          'source': source[0],
          }

    cmd = r"{objcopy} --only-keep-debug {source} {target}"

    cmd = cmd.format(**d)
    cmd = cmd.replace('\n', ' ')
    cmd = ' '.join(cmd.split())

    return cmd


def debugsymbols_print(target, source, env, executor=None):
    presentation = target[0]
    if 'fn_prettify_path' in env:
        presentation = env['fn_prettify_path'](presentation)
    retval = ' DBGSYMS  %s' % (presentation)
    if env['VERBOSE_OUTPUT']:
        retval += '\n%s' % (debugsymbols_generator(target, source, env, True))
    return retval

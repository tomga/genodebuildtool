
import os
import re

from SCons.Node import FS
from SCons.Script import Action, Builder
from SCons.Action import CommandGeneratorAction

def generate(env):
    '''
    CheckAbi(target, source)
    env.CheckAbi(target, source)

    CheckAbis source to target
    '''
    bldr = Builder(action = CommandGeneratorAction(generator = checkabi_generator,
                                                   kw = {'strfunction': checkabi_print}))
    env.Append(BUILDERS = {'CheckAbi' : bldr})


def exists(env):
    return True


def checkabi_generator(target, source, env, for_signature):

    d = { 'check_abi': env['CHECK_ABI'],
          'target': target[0],
          'source_so': source[0],
          'source_sym': source[1],
          }

    cmd = r"{check_abi} {source_so} {source_sym} && touch {target}"

    cmd = cmd.format(**d)
    cmd = cmd.replace('\n', ' ')
    cmd = ' '.join(cmd.split())

    return cmd


def checkabi_print(target, source, env, executor=None):
    presentation = target[0]
    if 'fn_prettify_path' in env:
        presentation = env['fn_prettify_path'](presentation)
    retval = ' CHECKABI %s' % (presentation)
    if env['VERBOSE_OUTPUT']:
        retval += '\n%s' % (checkabi_generator(target, source, env, True))
    return retval

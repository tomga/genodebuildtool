
import os
import re

from SCons.Node import FS
from SCons.Script import Action, Builder
from SCons.Action import CommandGeneratorAction

def generate(env):
    '''
    Strip(target, source)
    env.Strip(target, source)

    Strips source to target
    '''
    bldr = Builder(action = CommandGeneratorAction(generator = strip_generator,
                                                   kw = {'strfunction': strip_print}))
    env.Append(BUILDERS = {'Strip' : bldr})


def exists(env):
    return True


def strip_generator(target, source, env, for_signature):

    d = { 'strip': env['STRIP'],
          'target': target[0],
          'source': source[0],
          }

    cmd = r"{strip} -o {target} {source}"

    cmd = cmd.format(**d)
    cmd = cmd.replace('\n', ' ')
    cmd = ' '.join(cmd.split())

    return cmd


def strip_print(target, source, env):
    presentation = target[0]
    if 'fn_prettify_path' in env:
        presentation = env['fn_prettify_path'](presentation)
    retval = ' STRIP    %s' % (presentation)
    if env['VERBOSE_OUTPUT']:
        retval += '\n%s' % (strip_generator(target, source, env, True))
    return retval

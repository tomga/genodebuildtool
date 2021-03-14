
import os
import shutil

from SCons.Node import FS
from SCons.Script import Action, Builder

def generate(env):
    '''
    Copy(target, source)
    env.Copy(target, source)

    Makes a copy just like standard Copy Command action named "link_name" that points to the
    real file or directory "source". The link produced is always
    relative.
    '''
    bldr = Builder(action = Action(copy_builder,copy_print),
        single_target = True,
        single_source = True)
    env.Append(BUILDERS = {'Copy' : bldr})

def exists(env):
    return True

def copy_print(target, source, env, executor=None):
    presentation = target[0]
    if 'fn_prettify_path' in env:
        presentation = env['fn_prettify_path'](presentation)
    retval = ' COPY     %s' % (presentation)
    if env['VERBOSE_OUTPUT']:
        tgt = target[0]
        src = source[0]
        retval += '\ncp %s %s' % (src, tgt)
    return retval


def copy_builder(target, source, env):

    shutil.copy(source[0].abspath, target[0].abspath)

    return None

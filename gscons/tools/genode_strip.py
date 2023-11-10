
import os
import re

from SCons.Node import FS
from SCons.Script import Builder
from SCons.Action import Action, CommandGeneratorAction

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
          'strip_opts': env['STRIP_OPTIONS'] if 'STRIP_OPTIONS' in env else '',
          'target': target[0],
          'source': source[0],
          }

    cmd = r"{strip} {strip_opts} -o {target} {source}"

    cmd = cmd.format(**d)
    cmd = cmd.replace('\n', ' ')
    cmd = ' '.join(cmd.split())

    commands = [cmd]

    if len(source) > 1: # add gnu debuglink

        lnk = source[1].abspath
        src = source[0].abspath
        lnkdir,lnkname = os.path.split(lnk)
        srcrel = os.path.relpath(src,lnkdir)
        tgtdir,tgtname = os.path.split(str(target[0]))

        d = { 'objcopy': env['OBJCOPY'],
              'debuglink': srcrel,
              'tgtdir': tgtdir,
              'tgtname': tgtname,
              }
        cmd = r"cd {tgtdir} && {objcopy} --add-gnu-debuglink={debuglink} {tgtname}"

        cmd = cmd.format(**d)
        cmd = cmd.replace('\n', ' ')
        cmd = ' '.join(cmd.split())

        commands += [cmd]

    return Action(commands,
                  env['fn_fmt_out'](env['fn_prettify_path'](target[0]), 'STRIP', commands))


def strip_print(target, source, env, executor=None):
    presentation = target[0]
    if 'fn_prettify_path' in env:
        presentation = env['fn_prettify_path'](presentation)
    retval = ' STRIP    %s' % (presentation)
    if env['VERBOSE_OUTPUT']:
        retval += '\n%s' % ('\n'.join(strip_generator(target, source, env, True)))
    return retval

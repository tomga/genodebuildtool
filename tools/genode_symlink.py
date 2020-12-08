
## based on
## https://stackoverflow.com/questions/3532307/how-to-create-a-symbolic-link-with-scons

import os

from SCons.Node import FS
from SCons.Script import Action, Builder

def generate(env):
    '''
    SymLink(link_name,source)
    env.SymLink(link_name,source)

    Makes a symbolic link named "link_name" that points to the
    real file or directory "source". The link produced is always
    relative.
    '''
    bldr = Builder(action = Action(symlink_builder,symlink_print),
        target_factory = FS.File,
        source_factory = FS.Entry,
        single_target = True,
        single_source = True,
        emitter = symlink_emitter)
    env.Append(BUILDERS = {'SymLink' : bldr})

def exists(env):
    '''
    we could test if the OS supports symlinks here, or we could
    use copytree as an alternative in the builder.
    '''
    return True

def symlink_print(target, source, env, executor=None):
    presentation = target[0]
    if 'fn_prettify_path' in env:
        presentation = env['fn_prettify_path'](presentation)
    retval = ' SYMLINK  %s' % (presentation)
    if env['VERBOSE_OUTPUT']:
        lnk = target[0]
        src = os.path.relpath(source[0].abspath, target[0].abspath)
        # simulate ln to be conformant with make output
        retval += '\nln -sf %s %s' % (src, lnk)
    return retval

def symlink_emitter(target, source, env):
    '''
    This emitter removes the link if the source file name has changed
    since scons does not seem to catch this case.
    '''
    lnk = target[0].abspath
    src = source[0].abspath
    lnkdir,lnkname = os.path.split(lnk)
    srcrel = os.path.relpath(src,lnkdir)

    try:
        if os.path.exists(lnk):
            if os.readlink(lnk) != srcrel:
                os.remove(lnk)
    except AttributeError:
        # no symlink available, so we remove the whole tree? (or pass)
        #os.rmtree(lnk)
        print('no os.symlink capability on this system?')

    return (target, source)


def symlink_builder(target, source, env):
    lnk = target[0].abspath
    src = source[0].abspath
    lnkdir,lnkname = os.path.split(lnk)
    srcrel = os.path.relpath(src,lnkdir)

    try:
        os.symlink(srcrel,lnk)
    except AttributeError:
        # no symlink available, so we make a (deep) copy? (or pass)
        #os.copytree(srcrel,lnk)
        print('no os.symlink capability on this system?')

    return None

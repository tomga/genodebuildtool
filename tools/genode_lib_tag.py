
import os

from SCons.Script import Action, Builder

def generate(env):
    '''LibTag(tag_file, library_files)
    env.LibTag(tag_file, library_files)

    Creates a <lib>.lib.tag file from list of library file
    names. Content is mostly needed to deterministally detect if
    library has abi file build in case of shared library.

    NOTE: It is different from make build as make build tests for
    existance of abi file in build directory which is wrong as it may
    be a leftover after build of different library version.

    '''
    bldr = Builder(action = Action(lib_tag_builder,lib_tag_print))
    env.Append(BUILDERS = {'LibTag' : bldr})


def exists(env):
    '''
    we could test if the OS supports lib_tags here, or we could
    use copytree as an alternative in the builder.
    '''
    return True


def calculate_tag(source):
    tag = ('abi' if len([ s for s in source if str(s).endswith('.abi.so')]) > 0 else
           'so' if len([ s for s in source if str(s).endswith('.lib.so')]) > 0 else
           'a' if len([ s for s in source if str(s).endswith('.lib.a')]) > 0 else
           None)

    if tag is None:
        raise("LibTag: could not detect library tag: %s" % (str(list(map(str, source)))))
    return tag


def lib_tag_print(target, source, env):
    presentation = target[0]
    if 'fn_prettify_path' in env:
        presentation = env['fn_prettify_path'](presentation)
    retval = ' LIBTAG %s' % (presentation)
    if env['VERBOSE_OUTPUT']:
        tag_file = target[0]
        tag = calculate_tag(source)
        retval += '\necho %s > %s' % (tag, tag_file)
    return retval


def lib_tag_builder(target, source, env):
    tag_file = target[0].abspath
    tag = calculate_tag(source)

    with open(tag_file, 'w') as t:
        t.write(tag)

    return None

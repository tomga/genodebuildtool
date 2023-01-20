
import argparse
import collections
import os
import re
import shlex



def nodups(lst):
    return list(collections.OrderedDict.fromkeys(lst))


def path_clean(path, run_dir, abs_dir, rel_dir, modify_relatives):

    if (path.startswith('BLD/')):
        return path

    # print("path_clean: %s" % (str(path)))
    # print("       run: %s" % (str(run_dir)))
    # print("       abs: %s" % (str(abs_dir)))
    # print("       rel: %s" % (str(rel_dir)))
    # print("       mod: %s" % (str(modify_relatives)))
    path = os.path.normpath(path)

    if modify_relatives and not path.startswith('/'):
        path = os.path.normpath(os.path.join(run_dir, path))
    if path.startswith(abs_dir + '/'):
        path = path[len(abs_dir)+1:]
    if path.startswith(rel_dir):
        path = 'BLD%s' % (path[len(rel_dir):])
    else:
        path = path.replace('/' + rel_dir, '/BLD')

    return path


def arguments_print(opts):
    print("Arguments")
    for opt in vars(opts):
        print("   %s: %s" % (str(opt), str(getattr(opts, opt))))



def arg_parse_compiler(args_array):

    args_array = [ arg if arg != '-W' else '-W~' for arg in args_array ]

    argparser = argparse.ArgumentParser('gcc/g++')
    argparser.add_argument('SOURCES', action='append', default=[], nargs='*')
    argparser.add_argument('-c', action='store_true')
    argparser.add_argument('-g', action='store_true')
    argparser.add_argument('-O', action='append', default=[])
    argparser.add_argument('-std', action='append', default=[])
    argparser.add_argument('-m', action='append', default=[])
    argparser.add_argument('-mcmodel', action='append', default=[])
    argparser.add_argument('-nostdinc', action='store_true')
    argparser.add_argument('-nostdlib', action='store_true')
    argparser.add_argument('-static', action='store_true')
    argparser.add_argument('-shared', action='store_true')
    argparser.add_argument('-no-pie', action='store_true')
    argparser.add_argument('-o', dest='TARGETS', action='append', default=[], nargs=1)
    argparser.add_argument('-f', action='append', default=[])
    argparser.add_argument('-W', action='append', default=[])
    argparser.add_argument('-D', action='append', default=[])
    argparser.add_argument('-U', action='append', default=[])
    argparser.add_argument('-I', action='append', default=[])
    argparser.add_argument('-include', action='append', default=[])
    argparser.add_argument('-L', action='append', default=[])
    argparser.add_argument('-l', action='append', default=[])
    argparser.add_argument('-MMD', action='store_true')
    argparser.add_argument('-MP', action='store_true')
    argparser.add_argument('-MT', default=[])

    ### special treatment of linker flags
    argparser.add_argument('-LINKER_FLAGS')   # just a placeholder

    ldGroupStartIdx = args_array.index('-Wl,--start-group') if '-Wl,--start-group' in args_array else None
    ldGroupEndIdx = args_array.index('-Wl,--end-group') if '-Wl,--end-group' in args_array else None
    ldWholeArchiveOn = args_array.index('-Wl,--whole-archive') if '-Wl,--whole-archive' in args_array else None
    ldWholeArchiveOff = args_array.index('-Wl,--no-whole-archive') if '-Wl,--no-whole-archive' in args_array else None

    ldStartIdx = None
    if ldGroupStartIdx is not None:
        if ldWholeArchiveOn is not None:
            ldStartIdx = max(ldGroupStartIdx, ldWholeArchiveOn)
        else:
            ldStartIdx = ldGroupStartIdx
    else:
        ldStartIdx = ldWholeArchiveOn

    ldEndIdx = None
    if ldGroupEndIdx is not None:
        if ldWholeArchiveOff is not None:
            ldEndIdx = min(ldGroupEndIdx, ldWholeArchiveOff)
        else:
            ldEndIdx = ldGroupEndIdx
    else:
        ldEndIdx =ldWholeArchiveOff


    assert ldStartIdx is None and ldEndIdx is None or ldStartIdx is not None and ldEndIdx is not None
    ldGroup = []
    if ldStartIdx is not None:
        ldGroup = args_array[ldStartIdx + 1:ldEndIdx]
        args_array = args_array[0:ldStartIdx + 1] + args_array[ldEndIdx:]

    parsed_args = argparser.parse_args(args_array)

    linker_args = [ arg[2:] for arg in parsed_args.W if arg.startswith('l,') ]
    parsed_args.W = [ arg for arg in parsed_args.W if not arg.startswith('l,') ]
    parsed_args.LINKER_FLAGS = arg_parse_ld(linker_args)
    parsed_args.LINKER_FLAGS.SOURCES = [ ldGroup ]
    parsed_args.LINKER_FLAGS.TARGETS = [ [] ]

    #print("linker_args: %s" % (str(linker_args)))
    #arguments_print(parsed_args)

    return parsed_args


def arg_clean_compiler(args_tokenized, run_dir, abs_dir, rel_dir, options):

    opts = arg_parse_compiler(args_tokenized[1:])
    #arguments_print(opts)

    args_tokenized[0] = path_clean(args_tokenized[0], run_dir, abs_dir, rel_dir, False)

    res = [args_tokenized[0]]

    sources = [ '%s' % (path_clean(v, run_dir, abs_dir, rel_dir, True))
                for v in nodups(opts.SOURCES[0]) ]
    if len(opts.TARGETS) > 0:
        targets = [ '%s' % (path_clean(v, run_dir, abs_dir, rel_dir, True))
                    for v in nodups(opts.TARGETS[0]) ]
    else:
        targets = [ '%s' % (path_clean(os.path.join(run_dir, os.path.splitext(os.path.basename(v))[0] + '.o'),
                                       run_dir, abs_dir, rel_dir, True))
                    for v in nodups(opts.SOURCES[0]) ]

    if opts.c: res += ['-c']
    if opts.g: res += ['-g']
    res += [ '-O%s' % (v) for v in nodups(opts.O) ]
    res += [ '-std%s' % (v) for v in nodups(opts.std) ]
    res += [ '-m%s' % (v) for v in nodups(opts.m) ]
    res += [ '-mcmodel=%s' % (v) for v in nodups(opts.mcmodel) ]
    if opts.nostdinc: res += ['-nostdinc']
    if opts.nostdlib: res += ['-nostdlib']
    if opts.static: res += ['-static']
    if opts.static: res += ['-shared']
    if opts.no_pie: res += ['-no-pie']
    res += [ '-f%s' % (v) for v in nodups(opts.f) ]
    res += [ '-W%s' % (v if v != '~' else '') for v in sorted(nodups(opts.W)) ]
    res += [ '-D%s' % (v) for v in sorted(nodups(opts.D)) ]
    res += [ '-U%s' % (v) for v in sorted(nodups(opts.U)) ]
    inc = nodups([ '-I%s' % (path_clean(v, run_dir, abs_dir, rel_dir, True))
                   for v in nodups(opts.I) ])
    if 'noincsort' not in options:
        inc = sorted(inc)
    res += inc
    res += [ '-include %s' % (path_clean(v, run_dir, abs_dir, rel_dir, False))
             for v in opts.include ]
    res += [ '-L%s' % (path_clean(v, run_dir, abs_dir, rel_dir, False))
             for v in nodups(opts.L) ]
    res += [ '-l%s' % (v) for v in nodups(opts.l) ]
    #ignore
    # -MMD
    # -MP
    # -MT

    # linker options
    ld_res, ld_sources, ld_targets = arg_output_ld(opts.LINKER_FLAGS, run_dir, abs_dir, rel_dir, opts_prefix='-Wl,')
    res += ld_res

    res += sources

    res += [ '-o %s' % (v) for v in targets ]

    command = ' '.join(res)

    #print('arg_clean_compiler: %s' % (command))

    return (command, sources + ld_sources, targets + ld_targets)



def arg_parse_ar(args_array):

    argparser = argparse.ArgumentParser('ar')
    argparser.add_argument('-rcs', action='store_true')
    argparser.add_argument('TARGETS', action='append', nargs=1)
    argparser.add_argument('SOURCES', action='append', nargs='*')

    return argparser.parse_args(args_array)


def arg_clean_ar(args_tokenized, run_dir, abs_dir, rel_dir):

    opts = arg_parse_ar(args_tokenized[1:])
    #arguments_print(opts)

    res = [args_tokenized[0]]

    sources = [ '%s' % (path_clean(v, run_dir, abs_dir, rel_dir, True))
                for v in nodups(opts.SOURCES[0]) ]
    targets = [ '%s' % (path_clean(v, run_dir, abs_dir, rel_dir, True))
                for v in nodups(opts.TARGETS[0]) ]

    if opts.rcs: res += ['-rcs']
    res += targets
    res += sources

    command = ' '.join(res)

    return (command, sources, targets)



def arg_parse_ld(args_array):

    argparser = argparse.ArgumentParser('ld')

    argparser.add_argument('SOURCES', action='append', default=[], nargs='*')
    argparser.add_argument('-soname', action='append', default=[])
    argparser.add_argument('-shared', action='store_true')
    argparser.add_argument('-O', action='append', default=[])
    argparser.add_argument('--eh-frame-hdr', action='store_true')
    argparser.add_argument('-Bsymbolic-functions', action='store_true')
    argparser.add_argument('--version-script', action='append', default=[])
    argparser.add_argument('-T', action='append', default=[])
    argparser.add_argument('--entry', action='append', default=[])
    argparser.add_argument('-m', action='append', default=[])
    argparser.add_argument('-gc-sections', action='store_true')
    argparser.add_argument('-r', action='store_true')
    argparser.add_argument('-u', action='append', default=[])
    argparser.add_argument('-z', action='append', default=[])

    argparser.add_argument('-rpath-link', action='append', default=[])
    argparser.add_argument('--hash-style', action='append', default=[])
    argparser.add_argument('--dynamic-list', action='append', default=[])
    argparser.add_argument('-nostdlib', action='store_true')
    argparser.add_argument('--dynamic-linker', action='append', default=[])

    argparser.add_argument('--as-needed', action='store_true')

    argparser.add_argument('--whole-archive', action='store_true')
    argparser.add_argument('--start-group', action='store_true')
    argparser.add_argument('--end-group', action='store_true')
    argparser.add_argument('--no-whole-archive', action='store_true')
    argparser.add_argument('-o', dest='TARGETS', action='append', default=[], nargs=1)

    ### special treatment of ungrouped sources
    argparser.add_argument('-UNGROUPED_SOURCES')   # just a placeholder

    last_not_ungrouped_arg_index = len(args_array)-1
    if '--no-whole-archive' in args_array:
        last_not_ungrouped_arg_index = args_array.index('--no-whole-archive')

    retval = argparser.parse_args(args_array[:last_not_ungrouped_arg_index+1])
    retval.UNGROUPED_SOURCES = args_array[last_not_ungrouped_arg_index+1:]

    return retval


def arg_output_ld(args_parsed, run_dir, abs_dir, rel_dir, opts_prefix=None):

    opts = args_parsed

    res1 = []
    resS = []
    res2 = []

    sources = [ '%s' % (path_clean(v, run_dir, abs_dir, rel_dir, True))
                for v in nodups(opts.SOURCES[0]) ]
    targets = [ '%s' % (path_clean(v, run_dir, abs_dir, rel_dir, True))
                for v in nodups(opts.TARGETS[0]) ]

    for v in targets:
        res1 += [ '-o', v ]
    res1 += [ '-soname%s' % (v) for v in nodups(opts.soname) ]
    if opts.shared: res1 += ['-shared']
    res1 += [ '-O%s' % (v) for v in nodups(opts.O) ]
    if opts.eh_frame_hdr: res1 += ['--eh-frame-hdr']
    if opts.Bsymbolic_functions: res1 += ['-Bsymbolic-functions']
    for v in nodups(opts.version_script):
        res1 += [ '--version-script=%s' % (path_clean(v, run_dir, abs_dir, rel_dir, True)) ]
    for v in nodups(opts.T):
        if '=' not in v:
            res1 += [ '-T', path_clean(v, run_dir, abs_dir, rel_dir, True) ]
        else:
            res1 += [ '-T%s' % v ]
    for v in nodups(opts.entry):
        res1 += [ '--entry=%s' % (v) ]
    res1 += [ '-m%s' % (v) for v in nodups(opts.m) ]
    if opts.r: res1 += ['-r']
    if opts.gc_sections: res1 += ['-gc-sections']
    for v in nodups(opts.u):
        res1 += [ '-u', v ]
    for v in nodups(opts.z):
        res1 += [ '-z', v ]

    res1 += [ '-rpath-link=%s' % (os.path.normpath(v)) for v in nodups(opts.rpath_link) ]
    res1 += [ '--hash-style=%s' % (v) for v in nodups(opts.hash_style) ]
    res1 += [ '--dynamic-list=%s' % (path_clean(v, run_dir, abs_dir, rel_dir, True)) for v in nodups(opts.dynamic_list) ]
    if opts.nostdlib: res1 += ['-nostdlib']
    res1 += [ '--dynamic-linker=%s' % (v) for v in nodups(opts.dynamic_linker) ]

    if opts.as_needed: res1 += ['--as-needed']

    if opts.whole_archive: res1 += ['--whole-archive']
    if opts.start_group: res1 += ['--start-group']
    resS += sources
    if opts.end_group: res2 += ['--end-group']
    if opts.no_whole_archive: res2 += ['--no-whole-archive']

    if opts.UNGROUPED_SOURCES is not None:
        res2 += opts.UNGROUPED_SOURCES

    if opts_prefix is not None:
        res1 = [ opts_prefix + opt for opt in res1 ]
        res2 = [ opts_prefix + opt for opt in res2 ]

    return res1 + resS + res2, sources, targets


def arg_clean_ld(args_tokenized, run_dir, abs_dir, rel_dir):

    opts = arg_parse_ld(args_tokenized[1:])
    #arguments_print(opts)

    res = [args_tokenized[0]]

    ld_res, sources, targets = arg_output_ld(opts, run_dir, abs_dir, rel_dir)

    res += ld_res

    command = ' '.join(res)

    return (command, sources, targets)



def arg_parse_objcopy(args_array):

    argparser = argparse.ArgumentParser('objcopy')
    argparser.add_argument('-O', action='append', default=[])
    argparser.add_argument('--localize-symbol', action='append', default=[])
    argparser.add_argument('--redefine-sym', action='append', default=[])
    argparser.add_argument('SOURCES', action='append', default=[], nargs=1)
    argparser.add_argument('TARGETS', action='append', default=[], nargs=1)

    return argparser.parse_args(args_array)


def arg_clean_objcopy(args_tokenized, run_dir, abs_dir, rel_dir):

    opts = arg_parse_objcopy(args_tokenized[1:])
    #arguments_print(opts)

    res = [args_tokenized[0]]

    sources = [ '%s' % (path_clean(v, run_dir, abs_dir, rel_dir, True))
                for v in nodups(opts.SOURCES[0]) ]
    targets = [ '%s' % (path_clean(v, run_dir, abs_dir, rel_dir, True))
                for v in nodups(opts.TARGETS[0]) ]

    res += [ '-O %s' % (v) for v in nodups(opts.O) ]
    res += [ '--localize-symbol=%s' % (v) for v in nodups(opts.localize_symbol) ]
    res += [ '--redefine-sym %s' % (v) for v in nodups(opts.redefine_sym) ]

    res += sources
    res += targets

    command = ' '.join(res)

    return (command, sources, targets)



def arg_parse_binary(args_array):

    argparser = argparse.ArgumentParser('as')
    argparser.add_argument('-f', action='store_true')
    argparser.add_argument('-march', action='append', default=[])
    argparser.add_argument('--32', action='store_true')
    argparser.add_argument('SOURCES', action='append', default=[], nargs=1)
    argparser.add_argument('-o', dest='TARGETS', action='append', default=[], nargs=1)

    return argparser.parse_args(args_array)


def arg_clean_binary(args_tokenized, run_dir, abs_dir, rel_dir):

    # it should have form:
    # echo sth_with_incbin | as ..args..
    assert args_tokenized[0] == 'echo'
    assert args_tokenized[2] == '|'
    assert args_tokenized[3].endswith('as')

    src = args_tokenized[1].split('"')
    assert len(src) == 3
    assert src[0].endswith('; .incbin ')

    opts = arg_parse_binary(args_tokenized[4:])
    #arguments_print(opts)

    res = [args_tokenized[0]]

    source = path_clean(src[1], run_dir, abs_dir, rel_dir, True)
    res += [ r'"%s\"%s\"%s"' % (src[0], source, src[2]) ]

    res += [ '|' ]
    res += [ args_tokenized[3] ]

    if opts.f: res += ['-f']

    assert len(opts.SOURCES) == 1
    assert len(opts.SOURCES[0]) == 1
    assert opts.SOURCES[0][0] == '-'

    targets = [ '%s' % (path_clean(v, run_dir, abs_dir, rel_dir, True))
                for v in nodups(opts.TARGETS[0]) ]

    res += [ '-march=%s' % (v) for v in nodups(opts.march) ]
    if '32' in vars(opts) and str(getattr(opts, '32')): res += ['--32']

    res += [ '-o %s' % (v) for v in targets ]
    res += [ '-' ]

    command = ' '.join(res)

    return (command, [source], targets)



def arg_parse_strip(args_array):

    argparser = argparse.ArgumentParser('strip')
    argparser.add_argument('--strip-debug', action='store_true')
    argparser.add_argument('--strip-unneeded', action='store_true')
    argparser.add_argument('SOURCES', action='append', default=[], nargs=1)
    argparser.add_argument('-o', dest='TARGETS', action='append', default=[], nargs=1)

    return argparser.parse_args(args_array)


def arg_clean_strip(args_tokenized, run_dir, abs_dir, rel_dir):

    opts = arg_parse_strip(args_tokenized[1:])
    #arguments_print(opts)

    res = [args_tokenized[0]]

    sources = [ '%s' % (path_clean(v, run_dir, abs_dir, rel_dir, True))
                for v in nodups(opts.SOURCES[0]) ]
    targets = [ '%s' % (path_clean(v, run_dir, abs_dir, rel_dir, True))
                for v in nodups(opts.TARGETS[0]) ]

    if opts.strip_debug: res += ['--strip-debug']
    if opts.strip_unneeded: res += ['--strip-unneeded']
    res += [ '-o %s' % (v) for v in targets ]
    res += sources

    command = ' '.join(res)

    return (command, sources, targets)



def arg_clean_check_abi(args_tokenized, run_dir, abs_dir, rel_dir):

    ## extend original check_abi command with touching checked file
    if len(args_tokenized) == 3:
        checked_name = args_tokenized[1].replace('.so', '.checked')
        args_tokenized.extend(['&&', 'touch', checked_name])

    assert len(args_tokenized) == 6
    assert args_tokenized[3] == '&&'
    assert args_tokenized[4] == 'touch'

    res = args_tokenized

    res[0] = path_clean(res[0], run_dir, abs_dir, rel_dir, True)

    res[1] = path_clean(res[1], run_dir, abs_dir, rel_dir, True)
    res[2] = path_clean(res[2], run_dir, abs_dir, rel_dir, True)
    sources = [res[1], res[2]]

    res[5] = path_clean(res[5], run_dir, abs_dir, rel_dir, True)
    targets = [res[5]]

    command = ' '.join(res)

    return (command, sources, targets)



def arg_clean_perl(args_tokenized, run_dir, abs_dir, rel_dir):

    assert args_tokenized[-2] == '>'

    res = args_tokenized

    res[-3] = path_clean(res[-3], run_dir, abs_dir, rel_dir, True)
    sources = [res[-3]]

    res[-1] = path_clean(res[-1], run_dir, abs_dir, rel_dir, True)
    targets = [res[-1]]

    command = ' '.join(res)

    return (command, sources, targets)



def arg_parse_make(args_array, mk_params_paths, mk_params_std):

    # make copy as content is modified
    args_array = [ v for v in args_array ]

    for option in [] + mk_params_paths + mk_params_std:
        args_array = [ '--%s' % (v) if v.startswith(option + '=') else v for v in args_array ]

    argparser = argparse.ArgumentParser('make')
    argparser.add_argument('-C', action='append', default=[])
    for option in [] + mk_params_paths + mk_params_std:
        argparser.add_argument('--%s' % option, action='append', default=[])
    argparser.add_argument('TARGETS', action='append', default=[], nargs='*')

    return argparser.parse_args(args_array)


def arg_clean_make(args_tokenized, run_dir, abs_dir, rel_dir):

    mk_params_paths = [ 'O', 'CC' ]
    mk_params_std = [ 'ARCH', 'CROSS_COMPILE',
                      'KBUILD_BUILD_TIMESTAMP', 'KBUILD_BUILD_HOST', 'KBUILD_BUILD_USER' ]

    if (args_tokenized[-4] == '2>&1' and
        args_tokenized[-3] == '|' and
        args_tokenized[-2] == 'sed'):
        args_tokenized = args_tokenized[0:-4]

    opts = arg_parse_make(args_tokenized[1:], mk_params_paths, mk_params_std)
    #arguments_print(opts)

    res = [args_tokenized[0]]

    assert len(opts.C) <= 1
    realC_value = '.'
    if len(opts.C) == 1:
        realC_value = opts.C[0]
    realC_value = path_clean(realC_value, run_dir, abs_dir, rel_dir, True)
    res += [ '-C %s' % (realC_value) ]

    def calc_rel_path(path):
        return os.path.relpath(path, realC_value) if path.startswith('/') else path
    paramOvalues = nodups(getattr(opts, 'O'))
    paramOvalue = '.'
    if len(paramOvalues) != 0:
        paramOvalue = path_clean(calc_rel_path(paramOvalues[0]), run_dir, abs_dir, rel_dir, False)

    for option in mk_params_paths:
        res += [ '%s=%s' % (option, path_clean(calc_rel_path(v), run_dir, abs_dir, rel_dir, False))
                 for v in nodups(getattr(opts, option)) ]

    for option in mk_params_std:
        res += [ '%s=%s' % (option, v)
                 for v in nodups(getattr(opts, option)) ]
    if len(opts.TARGETS) > 0:
        res += opts.TARGETS[0]

    real_targets = opts.TARGETS[0] if len(opts.TARGETS[0]) > 0 else ['<default>']
    targets = [ os.path.normpath(os.path.join(realC_value, paramOvalue, '#' + v))
                for v in real_targets ]
    sources = []

    command = ' '.join(res)

    return (command, sources, targets)



def arg_parse_linux_scripts_config(args_array):

    argparser = argparse.ArgumentParser('linux/scripts/config')
    argparser.add_argument('--file', action='append', default=[])
    argparser.add_argument('--enable', action='append', default=[])
    argparser.add_argument('--disable', action='append', default=[])

    return argparser.parse_args(args_array)


def arg_clean_linux_scripts_config(args_tokenized, run_dir, abs_dir, rel_dir):

    opts = arg_parse_linux_scripts_config(args_tokenized[1:])
    #arguments_print(opts)

    res = [path_clean(args_tokenized[0], run_dir, abs_dir, rel_dir, True)]

    assert len(opts.file) <= 1
    tgt_file = '.config'
    if len(opts.file) == 1:
        tgt_file = opts.file[0]
    tgt_file = path_clean(tgt_file, run_dir, abs_dir, rel_dir, True)

    res += [ '--file %s' % (tgt_file) ]

    res += [ '--enable %s' % (v)
             for v in nodups(opts.enable)  ]
    res += [ '--disable %s' % (v)
             for v in nodups(opts.disable)  ]

    sources = []
    targets_annotation = ('#enable'  if len(opts.disable) == 0 else
                          '#disable' if len(opts.enable) == 0 else
                          '#')
    targets = [ tgt_file + targets_annotation ]

    command = ' '.join(res)

    return (command, sources, targets)



def arg_clean_sed(args_tokenized, run_dir, abs_dir, rel_dir):

    assert args_tokenized[-2] == '>'

    res = args_tokenized

    res[-3] = path_clean(res[-3], run_dir, abs_dir, rel_dir, True)
    sources = [res[-3]]

    res[-1] = path_clean(res[-1], run_dir, abs_dir, rel_dir, True)
    targets = [res[-1]]

    command = ' '.join(res)

    return (command, sources, targets)



def arg_clean_ln(args_tokenized, run_dir, abs_dir, rel_dir):

    res = args_tokenized

    if res[-1].endswith('/'):
        # handle case when directory is passed as target - heuristic
        res[-1] += os.path.basename(res[-2])

    res[-2] = path_clean(res[-2], os.path.abspath(res[-1]), abs_dir, '.', True)
    res[-2] = path_clean(res[-2], abs_dir, abs_dir, rel_dir, True)
    sources = [res[-2]]

    res[-1] = path_clean(res[-1], run_dir, abs_dir, rel_dir, True)
    targets = [res[-1]]

    command = ' '.join(res)

    return (command, sources, targets)


def arg_clean_cp(args_tokenized, run_dir, abs_dir, rel_dir):

    res = args_tokenized

    if res[-1].endswith('/'):
        # handle case when directory is passed as target - heuristic
        res[-1] += os.path.basename(res[-2])

    res[-2] = path_clean(res[-2], abs_dir, abs_dir, rel_dir, True)
    sources = [res[-2]]

    res[-1] = path_clean(res[-1], run_dir, abs_dir, rel_dir, True)
    targets = [res[-1]]

    command = ' '.join(res)

    return (command, sources, targets)


def arg_clean_ld_platform_symbol_map(args_tokenized, run_dir, abs_dir, rel_dir):
    assert args_tokenized[3] == 'sed'
    assert args_tokenized[4] == '-n'
    assert args_tokenized[-2] == '>'

    res = args_tokenized

    res[6] = path_clean(res[6], run_dir, abs_dir, rel_dir, True)
    sources = [res[6]]

    res[-1] = path_clean(res[-1], run_dir, abs_dir, rel_dir, True)
    targets = [res[-1]]

    command = ' '.join(res)

    return (command, sources, targets)



def arg_clean_ar_core_lib(args_tokenized, run_dir, abs_dir, rel_dir):

    assert args_tokenized[0] == '(echo'
    assert args_tokenized[1].split()[0] == 'create'
    assert args_tokenized[1].split()[1][-1] == ';'
    assert args_tokenized[2] == 'echo'
    assert args_tokenized[3] == '-e'
    assert args_tokenized[5] == 'echo'
    assert args_tokenized[6] == 'save;'
    assert args_tokenized[7] == 'echo'
    assert args_tokenized[8] == 'end;'
    assert args_tokenized[9] == ')'
    assert args_tokenized[10] == '|'
    assert args_tokenized[12] == '-M'

    res = args_tokenized

    res[1] = '"create %s";' % (path_clean(res[1].split()[1][:-1], run_dir, abs_dir, rel_dir, True))
    targets = [res[1]]

    addlibs_tokenized = arg_tokenize(res[4])
    assert addlibs_tokenized[-1][-1] == ';'
    addlibs_tokenized[-1] = addlibs_tokenized[-1][:-1]

    sources = [ path_clean(lib, run_dir, abs_dir, rel_dir, True)
                for addcmd, lib in zip(addlibs_tokenized[::2], addlibs_tokenized[1::2]) ]
    res[4] = '"%s";' % (' '.join(['\\naddlib %s' % lib for lib in sources]))

    res[6] = '"save";'
    res[8] = '"end";'

    command = ' '.join(res)

    return (command, sources, targets)



def arg_parse_dd(args_array):

    argparser = argparse.ArgumentParser('dd')
    argparser.add_argument('--of', action='append', default=[], nargs=1)
    argparser.add_argument('--bs', action='append', default=[], nargs=1)
    argparser.add_argument('--seek', action='append', default=[], nargs=1)
    argparser.add_argument('--count', action='append', default=[], nargs=1)
    argparser.add_argument('--conv', action='append', default=[], nargs=1)

    return argparser.parse_args(['--' + v for v in args_array])


def arg_clean_ld_elf_executable(args_tokenized, run_dir, abs_dir, rel_dir):

    assert len(args_tokenized) == 11
    assert args_tokenized[2] == '|'
    assert args_tokenized[3] == 'dd'
    assert args_tokenized[9] == '2>'
    assert args_tokenized[10] == '/dev/null'

    opts = arg_parse_dd(args_tokenized[4:9])
    #arguments_print(opts)

    res = args_tokenized[:4]

    sources = [ '%s' % (path_clean(v, run_dir, abs_dir, rel_dir, True))
                for v in nodups(opts.of[0]) ]
    targets = [ sources[0] + '[elf_exe]' ]

    res += ['of=%s' % sources[0] ]
    res += ['bs=%s' % opts.bs[0][0] ]
    res += ['seek=%s' % opts.seek[0][0] ]
    res += ['count=%s' % opts.count[0][0] ]
    res += ['conv=%s' % opts.conv[0][0] ]

    res += args_tokenized[9:]

    command = ' '.join(res)

    return (command, sources, targets)




libs_var_pattern = re.compile(r'^libs=(.*);$')

def arg_tokenize(args_string):
    args_tokenized = shlex.split(args_string)

    ## handle: libs=/some/path; cmd $libs/some/lib.lib.a
    libs_var_match = re.match(libs_var_pattern, args_tokenized[0])
    if libs_var_match:
        libs_var_value = libs_var_match.group(1)
        args_tokenized = [ t.replace('$libs', libs_var_value) for t in args_tokenized[1:]]

    # handle ccache
    if args_tokenized[0] == 'ccache':
        args_tokenized = args_tokenized[1:]

    return args_tokenized


def arg_clean(args_string, run_dir, abs_dir, rel_dir, options):
    try:
        return arg_clean_systemexit(args_string, run_dir, abs_dir, rel_dir, options)
    except SystemExit as e:
        print("Error during processing arguments of:")
        print("%s" % (args_string))
        raise e
    except Exception as e:
        print("Error during processing arguments of:")
        print("%s" % (args_string))
        raise e


def arg_clean_systemexit(args_string, run_dir, abs_dir, rel_dir, options):

    #print(args_string)
    args_tokenized = arg_tokenize(args_string)
    #print(str(args_tokenized))

    prg = args_tokenized[0]

    if (prg.endswith('gcc') or prg.endswith('g++')):
        return arg_clean_compiler(args_tokenized, run_dir, abs_dir, rel_dir, options)
    elif (prg.endswith('ar')):
        return arg_clean_ar(args_tokenized, run_dir, abs_dir, rel_dir)
    elif (prg.endswith('ld')):
        return arg_clean_ld(args_tokenized, run_dir, abs_dir, rel_dir)
    elif (prg.endswith('objcopy')):
        return arg_clean_objcopy(args_tokenized, run_dir, abs_dir, rel_dir)
    elif (prg.endswith('strip')):
        return arg_clean_strip(args_tokenized, run_dir, abs_dir, rel_dir)
    elif (prg.endswith('check_abi')):
        return arg_clean_check_abi(args_tokenized, run_dir, abs_dir, rel_dir)
    elif (prg == 'perl'):
        return arg_clean_perl(args_tokenized, run_dir, abs_dir, rel_dir)
    elif (prg == 'make'):
        return arg_clean_make(args_tokenized, run_dir, abs_dir, rel_dir)
    elif (prg.endswith('linux/scripts/config')):
        return arg_clean_linux_scripts_config(args_tokenized, run_dir, abs_dir, rel_dir)
    elif (prg.endswith('sed')):
        return arg_clean_sed(args_tokenized, run_dir, abs_dir, rel_dir)
    elif (prg.endswith('ln')):
        return arg_clean_ln(args_tokenized, run_dir, abs_dir, rel_dir)
    elif (prg.endswith('cp')):
        return arg_clean_cp(args_tokenized, run_dir, abs_dir, rel_dir)
    elif (prg.endswith('echo') and '.incbin' in args_string):
        return arg_clean_binary(args_tokenized, run_dir, abs_dir, rel_dir)
    elif (prg == '(echo' and 'global' in args_string and 'local' in args_string):
        return arg_clean_ld_platform_symbol_map(args_tokenized, run_dir, abs_dir, rel_dir)
    elif (prg == '(echo' and '"\\naddlib' in args_string and '"save";' in args_string and '"end";' in args_string):
        return arg_clean_ar_core_lib(args_tokenized, run_dir, abs_dir, rel_dir)
    elif (prg == 'printf' and args_tokenized[3] == 'dd'):
        return arg_clean_ld_elf_executable(args_tokenized, run_dir, abs_dir, rel_dir)
    elif prg.endswith(':'): # compiler/linker errors and warnings
        return (None, None, None)

    print("unsupported prog: %s" % prg)
    assert "unsupported prog: %s" % prg == None


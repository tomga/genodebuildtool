
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
    if path.startswith(rel_dir + '/'):
        path = 'BLD/%s' % (path[len(rel_dir)+1:])

    return path


def arguments_print(opts):
    print("Arguments")
    for opt in vars(opts):
        print("   %s: %s" % (str(opt), str(getattr(opts, opt))))



def arg_parse_compiler(args_array):

    argparser = argparse.ArgumentParser('gcc/g++')
    argparser.add_argument('SOURCES', action='append', default=[], nargs='+')
    argparser.add_argument('-c', action='store_true')
    argparser.add_argument('-g', action='store_true')
    argparser.add_argument('-O', action='append', default=[])
    argparser.add_argument('-std', action='append', default=[])
    argparser.add_argument('-m', action='append', default=[])
    argparser.add_argument('-mcmodel', action='append', default=[])
    argparser.add_argument('-nostdinc', action='store_true')
    argparser.add_argument('-nostdlib', action='store_true')
    argparser.add_argument('-o', dest='TARGETS', action='append', default=[], nargs=1)
    argparser.add_argument('-f', action='append', default=[])
    argparser.add_argument('-W', action='append', default=[])
    argparser.add_argument('-D', action='append', default=[])
    argparser.add_argument('-I', action='append', default=[])
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


def arg_clean_compiler(args_tokenized, run_dir, abs_dir, rel_dir):

    opts = arg_parse_compiler(args_tokenized[1:])
    #arguments_print(opts)

    res = [args_tokenized[0]]

    sources = [ '%s' % (path_clean(v, run_dir, abs_dir, rel_dir, True))
                for v in nodups(opts.SOURCES[0]) ]
    targets = [ '%s' % (path_clean(v, run_dir, abs_dir, rel_dir, True))
                for v in nodups(opts.TARGETS[0]) ]

    if opts.c: res += ['-c']
    if opts.g: res += ['-g']
    res += [ '-O%s' % (v) for v in nodups(opts.O) ]
    res += [ '-std%s' % (v) for v in nodups(opts.std) ]
    res += [ '-m%s' % (v) for v in nodups(opts.m) ]
    res += [ '-mcmodel=%s' % (v) for v in nodups(opts.mcmodel) ]
    if opts.nostdinc: res += ['-nostdinc']
    if opts.nostdlib: res += ['-nostdlib']
    res += [ '-f%s' % (v) for v in nodups(opts.f) ]
    res += [ '-W%s' % (v) for v in nodups(opts.W) ]
    res += [ '-D%s' % (v) for v in nodups(opts.D) ]
    res += [ '-I%s' % (path_clean(v, run_dir, abs_dir, rel_dir, False))
             for v in nodups(opts.I) ]
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
    argparser.add_argument('--eh-frame-hdr', action='store_true')
    argparser.add_argument('-T', action='append', default=[])
    argparser.add_argument('-m', action='append', default=[])
    argparser.add_argument('-gc-sections', action='store_true')
    argparser.add_argument('-r', action='store_true')
    argparser.add_argument('-u', action='append', default=[])
    argparser.add_argument('-z', action='append', default=[])

    argparser.add_argument('-rpath-link', action='append', default=[])
    argparser.add_argument('--dynamic-list', action='append', default=[])
    argparser.add_argument('-nostdlib', action='store_true')
    argparser.add_argument('--dynamic-linker', action='append', default=[])

    argparser.add_argument('--whole-archive', action='store_true')
    argparser.add_argument('--start-group', action='store_true')
    argparser.add_argument('--end-group', action='store_true')
    argparser.add_argument('--no-whole-archive', action='store_true')
    argparser.add_argument('-o', dest='TARGETS', action='append', default=[], nargs=1)

    return argparser.parse_args(args_array)


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
    if opts.eh_frame_hdr: res1 += ['--eh-frame-hdr']
    for v in nodups(opts.T):
        if '=' not in v:
            res1 += [ '-T', path_clean(v, run_dir, abs_dir, rel_dir, True) ]
        else:
            res1 += [ '-T%s' % v ]
    res1 += [ '-m%s' % (v) for v in nodups(opts.m) ]
    if opts.r: res1 += ['-r']
    if opts.gc_sections: res1 += ['-gc-sections']
    for v in nodups(opts.u):
        res1 += [ '-u', v ]
    for v in nodups(opts.z):
        res1 += [ '-z', v ]

    res1 += [ '-rpath-link=%s' % (v) for v in nodups(opts.rpath_link) ]
    res1 += [ '--dynamic-list=%s' % (path_clean(v, run_dir, abs_dir, rel_dir, True)) for v in nodups(opts.dynamic_list) ]
    if opts.nostdlib: res1 += ['-nostdlib']
    res1 += [ '--dynamic-linker=%s' % (v) for v in nodups(opts.dynamic_linker) ]

    if opts.whole_archive: res1 += ['--whole-archive']
    if opts.start_group: res1 += ['--start-group']
    resS += sources
    if opts.end_group: res2 += ['--end-group']
    if opts.no_whole_archive: res2 += ['--no-whole-archive']

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

    res += [ '--localize-symbol=%s' % (v) for v in nodups(opts.localize_symbol) ]
    res += [ '--redefine-sym %s' % (v) for v in nodups(opts.redefine_sym) ]

    res += sources
    res += targets

    command = ' '.join(res)

    return (command, sources, targets)



def arg_parse_binary(args_array):

    argparser = argparse.ArgumentParser('as')
    argparser.add_argument('-f', action='store_true')
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

    res += [ '-o %s' % (v) for v in targets ]
    res += [ '-' ]

    command = ' '.join(res)

    return (command, [source], targets)



def arg_parse_strip(args_array):

    argparser = argparse.ArgumentParser('strip')
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

    res += [ '-o %s' % (v) for v in targets ]
    res += sources

    command = ' '.join(res)

    return (command, sources, targets)



def arg_parse_sed(args_array):

    argparser = argparse.ArgumentParser('sed')
    argparser.add_argument('--localize-symbol', action='append', default=[])
    argparser.add_argument('--redefine-sym', action='append', default=[])
    argparser.add_argument('SOURCES', action='append', default=[], nargs=1)
    argparser.add_argument('TARGETS', action='append', default=[], nargs=1)

    return argparser.parse_args(args_array)


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

    res[-2] = path_clean(res[-2], os.path.abspath(res[-1]), abs_dir, '.', True)
    res[-2] = path_clean(res[-2], abs_dir, abs_dir, rel_dir, True)
    sources = [res[-2]]

    res[-1] = path_clean(res[-1], run_dir, abs_dir, rel_dir, True)
    targets = [res[-1]]

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

    return args_tokenized


def arg_clean(args_string, run_dir, abs_dir, rel_dir):

    #print(args_string)
    args_tokenized = arg_tokenize(args_string)
    #print(str(args_tokenized))

    prg = args_tokenized[0]

    if (prg.endswith('gcc') or prg.endswith('g++')):
        return arg_clean_compiler(args_tokenized, run_dir, abs_dir, rel_dir)
    elif (prg.endswith('ar')):
        return arg_clean_ar(args_tokenized, run_dir, abs_dir, rel_dir)
    elif (prg.endswith('ld')):
        return arg_clean_ld(args_tokenized, run_dir, abs_dir, rel_dir)
    elif (prg.endswith('objcopy')):
        return arg_clean_objcopy(args_tokenized, run_dir, abs_dir, rel_dir)
    elif (prg.endswith('strip')):
        return arg_clean_strip(args_tokenized, run_dir, abs_dir, rel_dir)
    elif (prg.endswith('sed')):
        return arg_clean_sed(args_tokenized, run_dir, abs_dir, rel_dir)
    elif (prg.endswith('ln')):
        return arg_clean_ln(args_tokenized, run_dir, abs_dir, rel_dir)
    elif (prg.endswith('echo') and '.incbin' in args_string):
        return arg_clean_binary(args_tokenized, run_dir, abs_dir, rel_dir)

    print("unspported prog: %s" % prg)
    assert "unspported prog: %s" % prg == None


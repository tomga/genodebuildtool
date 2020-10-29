
import argparse
import collections
import os
import shlex



def nodups(lst):
    return list(collections.OrderedDict.fromkeys(lst))


def path_clean(path, run_dir, abs_dir, rel_dir, modify_relatives):

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



def arg_parse_compile(args_array):

    argparser = argparse.ArgumentParser('gcc')
    argparser.add_argument('SOURCES', action='append', default=[], nargs='+')
    argparser.add_argument('-c', action='store_true')
    argparser.add_argument('-g', action='store_true')
    argparser.add_argument('-O', action='append', default=[])
    argparser.add_argument('-std', action='append', default=[])
    argparser.add_argument('-m', action='append', default=[])
    argparser.add_argument('-mcmodel', action='append', default=[])
    argparser.add_argument('-nostdinc', action='store_true')
    argparser.add_argument('-o', dest='TARGETS', action='append', default=[], nargs=1)

    argparser.add_argument('-f', action='append', default=[])
    argparser.add_argument('-W', action='append', default=[])
    argparser.add_argument('-D', action='append', default=[])
    argparser.add_argument('-I', action='append', default=[])
    argparser.add_argument('-MMD', action='store_true')
    argparser.add_argument('-MP', action='store_true')
    argparser.add_argument('-MT', default=[])

    return argparser.parse_args(args_array)


def arg_clean_compile(args_tokenized, run_dir, abs_dir, rel_dir):

    opts = arg_parse_compile(args_tokenized[1:])
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
    res += [ '-o %s' % (v) for v in targets ]
    res += [ '-f%s' % (v) for v in nodups(opts.f) ]
    res += [ '-W%s' % (v) for v in nodups(opts.W) ]
    res += [ '-D%s' % (v) for v in nodups(opts.D) ]
    res += [ '-I%s' % (path_clean(v, run_dir, abs_dir, rel_dir, False))
             for v in nodups(opts.I) ]
    #ignore
    # -MMD
    # -MP
    # -MT
    res += sources

    command = ' '.join(res)

    return (command, sources, targets)



def arg_parse_ar(args_array):

    argparser = argparse.ArgumentParser('ar')
    argparser.add_argument('-rcs', action='store_true')
    argparser.add_argument('TARGETS', action='append', nargs=1)
    argparser.add_argument('SOURCES', action='append', nargs='+')

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
    argparser.add_argument('SOURCES', action='append', default=[], nargs='+')
    argparser.add_argument('-soname', action='append', default=[])
    argparser.add_argument('-shared', action='store_true')
    argparser.add_argument('--eh-frame-hdr', action='store_true')
    argparser.add_argument('-T', action='append', default=[])
    argparser.add_argument('-m', action='append', default=[])
    argparser.add_argument('-gc-sections', action='store_true')
    argparser.add_argument('-r', action='store_true')
    argparser.add_argument('-u', action='append', default=[])
    argparser.add_argument('-z', action='append', default=[])
    argparser.add_argument('--whole-archive', action='store_true')
    argparser.add_argument('--start-group', action='store_true')
    argparser.add_argument('--end-group', action='store_true')
    argparser.add_argument('--no-whole-archive', action='store_true')
    argparser.add_argument('-o', dest='TARGETS', action='append', default=[], nargs=1)

    return argparser.parse_args(args_array)


def arg_clean_ld(args_tokenized, run_dir, abs_dir, rel_dir):

    opts = arg_parse_ld(args_tokenized[1:])
    print("ARGS: ld")
    arguments_print(opts)

    res = [args_tokenized[0]]

    sources = [ '%s' % (path_clean(v, run_dir, abs_dir, rel_dir, True))
                for v in nodups(opts.SOURCES[0]) ]
    targets = [ '%s' % (path_clean(v, run_dir, abs_dir, rel_dir, True))
                for v in nodups(opts.TARGETS[0]) ]

    res += [ '-o %s' % (v) for v in targets ]
    res += [ '-soname%s' % (v) for v in nodups(opts.soname) ]
    if opts.shared: res += ['-shared']
    if opts.eh_frame_hdr: res += ['--eh-frame-hdr']
    res += [ '-T%s' % (path_clean(v, run_dir, abs_dir, rel_dir, True)) for v in nodups(opts.T) ]
    res += [ '-m%s' % (v) for v in nodups(opts.m) ]
    if opts.r: res += ['-r']
    if opts.gc_sections: res += ['-gc-sections']
    res += [ '-u %s' % (v) for v in nodups(opts.u) ]
    res += [ '-z %s' % (v) for v in nodups(opts.z) ]

    if opts.whole_archive: res += ['--whole-archive']
    if opts.start_group: res += ['--start-group']
    res += sources
    if opts.end_group: res += ['--end-group']
    if opts.no_whole_archive: res += ['--no-whole-archive']

    command = ' '.join(res)

    return (command, sources, targets)



def arg_parse_objcopy(args_array):

    argparser = argparse.ArgumentParser('gcc')
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



def arg_parse_sed(args_array):

    argparser = argparse.ArgumentParser('gcc')
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
    sources = [res[-2]]

    res[-1] = path_clean(res[-1], run_dir, abs_dir, rel_dir, True)
    targets = [res[-1]]

    command = ' '.join(res)

    return (command, sources, targets)



def arg_clean(args_string, run_dir, abs_dir, rel_dir):

    args_tokenized = shlex.split(args_string)
    #print(str(args_tokenized))

    prg = args_tokenized[0]

    if (prg.endswith('gcc') or prg.endswith('g++')):
        return arg_clean_compile(args_tokenized, run_dir, abs_dir, rel_dir)
    elif (prg.endswith('ar')):
        return arg_clean_ar(args_tokenized, run_dir, abs_dir, rel_dir)
    elif (prg.endswith('ld')):
        return arg_clean_ld(args_tokenized, run_dir, abs_dir, rel_dir)
    elif (prg.endswith('objcopy')):
        return arg_clean_objcopy(args_tokenized, run_dir, abs_dir, rel_dir)
    elif (prg.endswith('sed')):
        return arg_clean_sed(args_tokenized, run_dir, abs_dir, rel_dir)
    elif (prg.endswith('ln')):
        return arg_clean_ln(args_tokenized, run_dir, abs_dir, rel_dir)

    print("unspported prog: %s" % prg)
    assert "unspported prog: %s" % prg == None


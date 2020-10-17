
import argparse
import collections
import os
import shlex



def arg_parse_compile(args_array):

    argparser = argparse.ArgumentParser('gcc')
    argparser.add_argument('SOURCES', action='append', default=[])
    argparser.add_argument('-c', action='store_true')
    argparser.add_argument('-g', action='store_true')
    argparser.add_argument('-O', action='append', default=[])
    argparser.add_argument('-std', action='append', default=[])
    argparser.add_argument('-m', action='append', default=[])
    argparser.add_argument('-mcmodel', action='append', default=[])
    argparser.add_argument('-nostdinc', action='store_true')
    argparser.add_argument('-o', action='append', default=[])

    argparser.add_argument('-f', action='append', default=[])
    argparser.add_argument('-W', action='append', default=[])
    argparser.add_argument('-D', action='append', default=[])
    argparser.add_argument('-I', action='append', default=[])
    argparser.add_argument('-MMD', action='store_true')
    argparser.add_argument('-MP', action='store_true')
    argparser.add_argument('-MT', default=[])

    return argparser.parse_args(args_array)


def nodups(lst):
    return list(collections.OrderedDict.fromkeys(lst))


def path_clean(path, paths_conf, modify_relatives):

    path = os.path.normpath(path)

    if modify_relatives and not path.startswith('/'):
        path = os.path.join(paths_conf['run'], path)
    if path.startswith(paths_conf['abs'] + '/'):
        path = path[len(paths_conf['abs'])+1:]
    if path.startswith(paths_conf['rel'] + '/'):
        path = 'BLD/%s' % (path[len(paths_conf['rel'])+1:])
    return path


def arg_clean_compile(args_string, paths_conf):

    args_tokenized = shlex.split(args_string)
    print(str(args_tokenized))

    opts = arg_parse_compile(args_tokenized[1:])
    arguments_print(opts)

    res = [args_tokenized[0]]

    if opts.c: res += ['-c']
    if opts.g: res += ['-g']
    res += [ '-O%s' % (v) for v in nodups(opts.O) ]
    res += [ '-std%s' % (v) for v in nodups(opts.std) ]
    res += [ '-m%s' % (v) for v in nodups(opts.m) ]
    res += [ '-mcmodel=%s' % (v) for v in nodups(opts.mcmodel) ]
    if opts.nostdinc: res += ['-nostdinc']
    res += [ '-o%s' % (path_clean(v, paths_conf, True)) for v in nodups(opts.o) ]
    res += [ '-f%s' % (v) for v in nodups(opts.f) ]
    res += [ '-W%s' % (v) for v in nodups(opts.W) ]
    res += [ '-D%s' % (v) for v in nodups(opts.D) ]
    res += [ '-I%s' % (path_clean(v, paths_conf, False)) for v in nodups(opts.I) ]
    #ignore
    # -MMD
    # -MP
    # -MT
    res += [ '%s' % (path_clean(v, paths_conf, True)) for v in nodups(opts.SOURCES) ]

    return ' '.join(res)


def arguments_print(opts):
    print("Arguments")
    for opt in vars(opts):
        print("   %s: %s" % (str(opt), str(getattr(opts, opt))))




if __name__ == "__main__":

    paths_s = { 'abs' : '/projects/genode/genode',
                'rel' : 'build/linux_s',
                'run' : '/projects/genode/genode',
                }

    paths_t = { 'abs' : '/projects/genode/genode',
                'rel' : 'build/linux_t',
                'run' : '/projects/genode/genode/build/linux_t/var/libcache/base-linux-common',
                }
    
    test_command_s = "/usr/local/genode/tool/19.05/bin/genode-x86-g++ -o build/linux_s/var/libcache/base-linux-common/mutex.o -c -D_GNU_SOURCE -ffunction-sections -fno-strict-aliasing -nostdinc -g -m64 -mcmodel=large -O2 -Wall -Wno-error=implicit-fallthrough -fPIC -Wextra -Weffc++ -Werror -Wsuggest-override -std=gnu++17 -fPIC -I. -Irepos/base-linux/src/include -Irepos/base/src/include -Irepos/base/include/spec/x86 -Irepos/os/include/spec/x86 -Irepos/base/include/spec/x86_64 -Irepos/os/include/spec/x86_64 -Irepos/base/include/spec/64bit -Irepos/base/include -Irepos/os/include -Irepos/demo/include -I/usr/local/genode/tool/19.05/lib/gcc/x86_64-pc-elf/8.3.0/include -Irepos/base-linux/src/lib/syscall -I/usr/include -I/usr/include/x86_64-linux-gnu repos/base/src/lib/base/mutex.cc"
    test_command_t = "/usr/local/genode/tool/19.05/bin/genode-x86-g++  -D_GNU_SOURCE -ffunction-sections -fno-strict-aliasing -nostdinc -g -m64 -mcmodel=large -O2 -MMD -MP -MT 'mutex.o mutex.d' -Wall -Wno-error=implicit-fallthrough  -fPIC -Wall -Wno-error=implicit-fallthrough -Wextra -Weffc++ -Werror -Wsuggest-override -std=gnu++17 -I. -I/projects/genode/genode/repos/base-linux/src/include -I/projects/genode/genode/repos/base/src/include -I/projects/genode/genode/repos/base/include/spec/x86 -I/projects/genode/genode/repos/os/include/spec/x86 -I/projects/genode/genode/repos/base/include/spec/x86_64 -I/projects/genode/genode/repos/os/include/spec/x86_64 -I/projects/genode/genode/repos/base/include/spec/64bit -I/projects/genode/genode/repos/base/include -I/projects/genode/genode/repos/os/include -I/projects/genode/genode/repos/demo/include -I/usr/local/genode/tool/19.05/bin/../lib/gcc/x86_64-pc-elf/8.3.0/include -I/projects/genode/genode/repos/base-linux/src/lib/syscall/ -I/usr/include -I/usr/include/x86_64-linux-gnu -I/usr/include/x86_64-linux-gnu -c /projects/genode/genode/repos/base/src/lib/base/mutex.cc -o mutex.o"

    clean_s = arg_clean_compile(test_command_s, paths_s)
    clean_t = arg_clean_compile(test_command_t, paths_t)
    
    print('%s' % (clean_s))
    print('%s' % (clean_t))
    print("Result: %s" % ("OK" if clean_s == clean_t else "ERROR"))

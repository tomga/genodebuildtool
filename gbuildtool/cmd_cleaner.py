
from gbuildtool import arg_cleaner



def commands_clean(cmd_lines, run_dir, abs_dir, rel_dir):
    result = []
    for unstripped in cmd_lines:

        orig = unstripped.strip()

        # specially accepted
        special_accepted = False
        if orig.startswith('sed '):
            special_accepted = True

        # unstripped negative checks
        if (not special_accepted and unstripped.startswith(' ')):
            continue

        # stripped negative checks
        if (orig.startswith('rm ') or
            (orig.startswith('echo ') and ' .incbin ' not in orig) or
            orig.startswith('for ') or
            orig.startswith('checking library dependencies') or
            orig.startswith('make ') or
            orig.startswith('touch ') or
            orig.startswith('mkdir ') or
            orig.startswith('scons:') or
            orig.startswith('In file ') or
            orig == 'true' or
            orig.startswith('compilation terminated.') or
            orig.split()[0].endswith(':') or
            '->' in orig or
            '~~~' in orig or
            orig.startswith('ln -sf `which ccache') or
            False):
            continue

        #print('cmd: %s' % orig)

        (cmd_noincsort, src, tgt) = arg_cleaner.arg_clean(orig, run_dir, abs_dir, rel_dir, ['noincsort'])
        (cmd, src, tgt) = arg_cleaner.arg_clean(orig, run_dir, abs_dir, rel_dir, [])

        if cmd is None:
            continue

        result += [(cmd, src, tgt, orig, cmd_noincsort)]

    return result


if __name__ == "__main__":

    paths_s = { 'abs' : '/projects/genode/genode_staging',
                'rel' : 'build/arm7_s',
                'run' : '/projects/genode/genode_staging',
                }

    paths_m = { 'abs' : '/projects/genode/genode_staging',
                'rel' : 'build/arm7_m',
                'run' : '/projects/genode/genode_staging/build/arm7_m/var/libcache/vfs',
                }

    test_command_s = "repos/base/../../tool/check_abi build/arm7_s/var/libcache/vfs/vfs.lib.so repos/os/lib/symbols/vfs && touch build/arm7_s/var/libcache/vfs/vfs.lib.checked"
    test_command_m = "/projects/genode/genode_staging/repos/base/../../tool/check_abi vfs.lib.so /projects/genode/genode_staging/repos/os/lib/symbols/vfs && touch vfs.lib.checked"

    #test_command_s = "/usr/local/genode/tool/19.05/bin/genode-x86-ar -rcs build/linux_s/var/libcache/cxx/cxx.lib.a build/linux_s/var/libcache/cxx/supc++.o build/linux_s/var/libcache/cxx/unwind.o"
    #test_command_m = "/usr/local/genode/tool/19.05/bin/genode-x86-ar -rcs cxx.lib.a supc++.o unwind.o"

    #test_command_s = "/usr/local/genode/tool/19.05/bin/genode-x86-g++ -o build/linux_s/var/libcache/cxx/emutls.o -c -ffunction-sections -fno-strict-aliasing -g -m64 -mcmodel=large -O2 -Wall -Wno-error=implicit-fallthrough -fPIC -Wextra -Weffc++ -Werror -Wsuggest-override -std=gnu++17 -fPIC -I. -Irepos/base/src/include -Irepos/base/include/spec/x86 -Irepos/os/include/spec/x86 -Irepos/base/include/spec/x86_64 -Irepos/os/include/spec/x86_64 -Irepos/base/include/spec/64bit -Irepos/base/include -Irepos/os/include -Irepos/demo/include -I/usr/local/genode/tool/19.05/lib/gcc/x86_64-pc-elf/8.3.0/include repos/base/src/lib/cxx/emutls.cc"
    #test_command_m = "/usr/local/genode/tool/19.05/bin/genode-x86-g++  -ffunction-sections -fno-strict-aliasing  -g -m64 -mcmodel=large -O2 -MMD -MP -MT 'emutls.o emutls.d' -Wall -Wno-error=implicit-fallthrough -Wno-error=implicit-fallthrough  -fPIC -ffunction-sections -fno-strict-aliasing  -g -m64 -mcmodel=large -O2 -MMD -MP -MT 'emutls.o emutls.d' -Wall -Wno-error=implicit-fallthrough -Wno-error=implicit-fallthrough  -fPIC -Wall -Wno-error=implicit-fallthrough -Wno-error=implicit-fallthrough -Wextra -Weffc++ -Werror -Wsuggest-override -std=gnu++17 -ffunction-sections -fno-strict-aliasing  -g -m64 -mcmodel=large -O2 -MMD -MP -MT 'emutls.o emutls.d' -Wall -Wno-error=implicit-fallthrough -Wno-error=implicit-fallthrough  -fPIC -ffunction-sections -fno-strict-aliasing  -g -m64 -mcmodel=large -O2 -MMD -MP -MT 'emutls.o emutls.d' -Wall -Wno-error=implicit-fallthrough -Wno-error=implicit-fallthrough  -fPIC -Wall -Wno-error=implicit-fallthrough -Wno-error=implicit-fallthrough -Wextra -Weffc++ -Werror -Wsuggest-override -std=gnu++17 -I. -I/projects/genode/genode/repos/base/src/include -I/projects/genode/genode/repos/base/include/spec/x86 -I/projects/genode/genode/repos/os/include/spec/x86 -I/projects/genode/genode/repos/base/include/spec/x86_64 -I/projects/genode/genode/repos/os/include/spec/x86_64 -I/projects/genode/genode/repos/base/include/spec/64bit -I/projects/genode/genode/repos/base/include -I/projects/genode/genode/repos/os/include -I/projects/genode/genode/repos/demo/include -I/usr/local/genode/tool/19.05/bin/../lib/gcc/x86_64-pc-elf/8.3.0/include -c /projects/genode/genode/repos/base/src/lib/cxx/emutls.cc -o emutls.o"


    #test_command_m = "/usr/local/genode/tool/19.05/bin/genode-x86-ld -o ld.abi.so -soname=ld.lib.so -shared --eh-frame-hdr -T/projects/genode/genode/repos/base/src/lib/ldso/linker.ld -melf_x86_64 -gc-sections -z max-page-size=0x1000 -T /projects/genode/genode/repos/base/src/ld/genode_rel.ld --whole-archive --start-group ld.symbols.o --end-group --no-whole-archive"

    clean_s, sources_s, targets_s, orig_s, noincsort_s = commands_clean([test_command_s], paths_s['run'], paths_s['abs'], paths_s['rel'])[0]
    clean_m, sources_m, targets_m, orig_m, noincsort_m = commands_clean([test_command_m], paths_m['run'], paths_m['abs'], paths_m['rel'])[0]

    print('%s' % (clean_s))
    print('%s' % (clean_m))
    print("Result: %s" % ("OK" if clean_s == clean_m else "ERROR"))

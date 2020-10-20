
import arg_cleaner



def cmd_clean(cmd_lines, run_dir, abs_dir, rel_dir):

    orig = cmd_lines[0] if not cmd_lines[0].startswith('rm ') else cmd_lines[1]
    src = None
    tgt = None

    #print('cmd: %s' % orig)

    if (orig.startswith('checking library dependencies') or
        orig.startswith('make ') or
        orig.startswith('scons:')):
        return (None, None, None, None)

    (cmd, src, tgt) = arg_cleaner.arg_clean(orig, run_dir, abs_dir, rel_dir)

    return (cmd, src, tgt, orig)



if __name__ == "__main__":

    paths_s = { 'abs' : '/projects/genode/genode',
                'rel' : 'build/linux_s',
                'run' : '/projects/genode/genode',
                }

    paths_t = { 'abs' : '/projects/genode/genode',
                'rel' : 'build/linux_t',
                'run' : '/projects/genode/genode/build/linux_t/var/libcache/cxx',
                }

    test_command_s = "/usr/local/genode/tool/19.05/bin/genode-x86-gcc -o build/linux_s/var/libcache/cxx/unwind.o -c -ffunction-sections -fno-strict-aliasing -g -m64 -mcmodel=large -O2 -Wall -Wno-error=implicit-fallthrough -fPIC -fPIC -I. -Irepos/base/src/include -Irepos/base/include/spec/x86 -Irepos/os/include/spec/x86 -Irepos/base/include/spec/x86_64 -Irepos/os/include/spec/x86_64 -Irepos/base/include/spec/64bit -Irepos/base/include -Irepos/os/include -Irepos/demo/include -I/usr/local/genode/tool/19.05/lib/gcc/x86_64-pc-elf/8.3.0/include repos/base/src/lib/cxx/unwind.c"
    test_command_t = "/usr/local/genode/tool/19.05/bin/genode-x86-gcc  -ffunction-sections -fno-strict-aliasing  -g -m64 -mcmodel=large -O2 -MMD -MP -MT 'unwind.o unwind.d' -Wall -Wno-error=implicit-fallthrough -Wno-error=implicit-fallthrough  -fPIC -ffunction-sections -fno-strict-aliasing  -g -m64 -mcmodel=large -O2 -MMD -MP -MT 'unwind.o unwind.d' -Wall -Wno-error=implicit-fallthrough -Wno-error=implicit-fallthrough  -fPIC -ffunction-sections -fno-strict-aliasing  -g -m64 -mcmodel=large -O2 -MMD -MP -MT 'unwind.o unwind.d' -Wall -Wno-error=implicit-fallthrough -Wno-error=implicit-fallthrough  -fPIC -ffunction-sections -fno-strict-aliasing  -g -m64 -mcmodel=large -O2 -MMD -MP -MT 'unwind.o unwind.d' -Wall -Wno-error=implicit-fallthrough -Wno-error=implicit-fallthrough  -fPIC -I. -I/projects/genode/genode/repos/base/src/include -I/projects/genode/genode/repos/base/include/spec/x86 -I/projects/genode/genode/repos/os/include/spec/x86 -I/projects/genode/genode/repos/base/include/spec/x86_64 -I/projects/genode/genode/repos/os/include/spec/x86_64 -I/projects/genode/genode/repos/base/include/spec/64bit -I/projects/genode/genode/repos/base/include -I/projects/genode/genode/repos/os/include -I/projects/genode/genode/repos/demo/include -I/usr/local/genode/tool/19.05/bin/../lib/gcc/x86_64-pc-elf/8.3.0/include -c /projects/genode/genode/repos/base/src/lib/cxx/unwind.c -o unwind.o"

    #test_command_s = "/usr/local/genode/tool/19.05/bin/genode-x86-ar -rcs build/linux_s/var/libcache/cxx/cxx.lib.a build/linux_s/var/libcache/cxx/supc++.o build/linux_s/var/libcache/cxx/unwind.o"
    #test_command_t = "/usr/local/genode/tool/19.05/bin/genode-x86-ar -rcs cxx.lib.a supc++.o unwind.o"

    test_command_s = "/usr/local/genode/tool/19.05/bin/genode-x86-g++ -o build/linux_s/var/libcache/cxx/emutls.o -c -ffunction-sections -fno-strict-aliasing -g -m64 -mcmodel=large -O2 -Wall -Wno-error=implicit-fallthrough -fPIC -Wextra -Weffc++ -Werror -Wsuggest-override -std=gnu++17 -fPIC -I. -Irepos/base/src/include -Irepos/base/include/spec/x86 -Irepos/os/include/spec/x86 -Irepos/base/include/spec/x86_64 -Irepos/os/include/spec/x86_64 -Irepos/base/include/spec/64bit -Irepos/base/include -Irepos/os/include -Irepos/demo/include -I/usr/local/genode/tool/19.05/lib/gcc/x86_64-pc-elf/8.3.0/include repos/base/src/lib/cxx/emutls.cc"
    test_command_t = "/usr/local/genode/tool/19.05/bin/genode-x86-g++  -ffunction-sections -fno-strict-aliasing  -g -m64 -mcmodel=large -O2 -MMD -MP -MT 'emutls.o emutls.d' -Wall -Wno-error=implicit-fallthrough -Wno-error=implicit-fallthrough  -fPIC -ffunction-sections -fno-strict-aliasing  -g -m64 -mcmodel=large -O2 -MMD -MP -MT 'emutls.o emutls.d' -Wall -Wno-error=implicit-fallthrough -Wno-error=implicit-fallthrough  -fPIC -Wall -Wno-error=implicit-fallthrough -Wno-error=implicit-fallthrough -Wextra -Weffc++ -Werror -Wsuggest-override -std=gnu++17 -ffunction-sections -fno-strict-aliasing  -g -m64 -mcmodel=large -O2 -MMD -MP -MT 'emutls.o emutls.d' -Wall -Wno-error=implicit-fallthrough -Wno-error=implicit-fallthrough  -fPIC -ffunction-sections -fno-strict-aliasing  -g -m64 -mcmodel=large -O2 -MMD -MP -MT 'emutls.o emutls.d' -Wall -Wno-error=implicit-fallthrough -Wno-error=implicit-fallthrough  -fPIC -Wall -Wno-error=implicit-fallthrough -Wno-error=implicit-fallthrough -Wextra -Weffc++ -Werror -Wsuggest-override -std=gnu++17 -I. -I/projects/genode/genode/repos/base/src/include -I/projects/genode/genode/repos/base/include/spec/x86 -I/projects/genode/genode/repos/os/include/spec/x86 -I/projects/genode/genode/repos/base/include/spec/x86_64 -I/projects/genode/genode/repos/os/include/spec/x86_64 -I/projects/genode/genode/repos/base/include/spec/64bit -I/projects/genode/genode/repos/base/include -I/projects/genode/genode/repos/os/include -I/projects/genode/genode/repos/demo/include -I/usr/local/genode/tool/19.05/bin/../lib/gcc/x86_64-pc-elf/8.3.0/include -c /projects/genode/genode/repos/base/src/lib/cxx/emutls.cc -o emutls.o"

    clean_s, sources_s, targets_s, orig_s = cmd_clean([test_command_s], paths_s['run'], paths_s['abs'], paths_s['rel'])
    clean_t, sources_t, targets_t, orig_t = cmd_clean([test_command_t], paths_t['run'], paths_t['abs'], paths_t['rel'])

    print('%s' % (clean_s))
    print('%s' % (clean_t))
    print("Result: %s" % ("OK" if clean_s == clean_t else "ERROR"))

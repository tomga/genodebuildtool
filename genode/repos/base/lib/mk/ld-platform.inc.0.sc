
import SCons.Action

def process_mk_overlay(mk_file, build_env):

    env = build_env.scons_env

    include_mk = build_env.get_mk_cache().get_parsed_mk(mk_file, no_overlay=True)
    include_mk.process(build_env)

    ld_file = env['fn_localize_path']('%s/lib/symbols/ld' % (env['BASE_DIR']))
    map_file = env['fn_unsconsify_path'](env['fn_target_path']('symbol.map'))
    map_cmd = r"""(echo -e "{\n\tglobal:";
                   sed -n "s/^\(\w\+\) .*/\t\t\1;/p" %s;
                   echo -e "\tlocal: *;\n};") > %s""" % (ld_file, map_file)
    map_cmd = map_cmd.replace('\n', ' ')
    map_tgt = env.Command(
        target=map_file,
        source=ld_file,
        action=SCons.Action.Action(map_cmd,
                                   env['fn_fmt_out'](map_file, 'CONVERT', map_cmd)))

    if ('linux' in build_env.var_values('SPECS')
        and env['fn_current_target_type']() == 'lib'):

        lib_so = env['fn_unsconsify_path'](env['fn_target_path']('ld-linux.lib.so'))
        exe_cmd = r"""printf "\x02" |
	          dd of=%s bs=1 seek=16 count=1 conv=notrunc
	          2> /dev/null""" % (lib_so)
        exe_cmd = exe_cmd.replace('\n', ' ')
        exe_cmd_str = env['fn_fmt_out'](lib_so, 'CONVERT', exe_cmd)

        delayed_action = lambda : env.AddPostAction('#' + lib_so,
                                                    SCons.Action.Action(exe_cmd, exe_cmd_str))
        env['fn_add_post_process_action'](delayed_action)
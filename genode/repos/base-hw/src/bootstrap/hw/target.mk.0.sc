
import os
from gscons import genode_prog
import SCons.Action


class GenodeBaseHwMkProg(genode_prog.GenodeMkProg):

    def process_target(self):

        super().process_target()

        env = self.env
        build_env = self.build_env

        ## NOTICE: ignoring LIBCXX_GCC as it is only set in cxx.mk and it
        ## seems that its value cannot get here

        prog_link_items = list(map(str, env['PROG_LINK_ITEMS']))
        env['fn_debug']("%s: %s" % ('PROG_LINK_ITEMS', str(prog_link_items)))

        env['LD_MARCH'] = build_env.var_value('LD_MARCH')
        env['fn_debug']("%s: %s" % ('LD_MARCH', env['LD_MARCH']))

        bootstrap_obj_basename = build_env.var_value('BOOTSTRAP_OBJ')
        bootstrap_obj = env['fn_sc_tgt_path'](bootstrap_obj_basename)
        env['fn_debug']("%s: %s" % ('bootstrap_obj', str(bootstrap_obj)))

        prog_targets = []

        env['MERGECOM'] = "${LD} ${LD_MARCH} -u _start --whole-archive -r ${SOURCES} -o ${TARGET}"
        bootstrap_obj_o = env.Command(
            target=str(bootstrap_obj),
            source=prog_link_items,
            action=SCons.Action.Action("$MERGECOM", "$MERGECOMSTR")
        )
        prog_targets.append(bootstrap_obj_o)

        # NOTE: ignoring check for INSTALL_DIR and DEBUG_DIR as it seems
        # they are always defined

        # stripped version
        strip_tgt = env.Strip(target=env['fn_sc_tgt_path']('%s.stripped' % (bootstrap_obj_basename)),
                              STRIP_OPTIONS='--strip-debug',
                              source=bootstrap_obj_o)
        prog_targets.append(strip_tgt)

        # symlink to stripped version
        inst_prog_tgt = env.SymLink(source = strip_tgt,
                                    target = env['fn_sconsify_path'](os.path.join(env['INSTALL_DIR'],
                                                                                  bootstrap_obj_basename)))
        prog_targets.append(inst_prog_tgt)


        # symlink to debug version
        dbg_prog_tgt = env.SymLink(source = bootstrap_obj_o,
                                   target = env['fn_sconsify_path'](os.path.join(env['DEBUG_DIR'],
                                                                                 bootstrap_obj_basename)))
        ## NOTICE: for some reason it is not built in mk build when target
        ## is bootstrap/hw so disabling here too
        # prog_targets.append(dbg_prog_tgt)

        return env.Alias(env['fn_current_target_alias'](), prog_targets)


def process_prog_overlay(prog_name, env, prog_mk_file, prog_mk_repo, build_env):

    prog = GenodeBaseHwMkProg(prog_name, env, prog_mk_file, prog_mk_repo, build_env)
    prog.disable_overlay()
    prog.process_load()

    return prog

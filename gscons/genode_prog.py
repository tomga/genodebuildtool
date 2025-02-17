
import os
import re
import subprocess

import SCons.Action

# debug support
import pprint

from gscons import mkevaluator
from gscons import mkparser
from gscons import scmkevaluator

from gscons import genode_build_helper
from gscons import genode_target
from gscons import genode_tools as tools


class GenodeProg(genode_target.GenodeTarget):

    def __init__(self, prog_name, env):

        self.prog_name = prog_name
        super().__init__(prog_name, 'program', 'PRG', env)



class GenodeDisabledProg(GenodeProg):

    def __init__(self, prog_name, env, disabled_message):

        super().__init__(prog_name, env)

        self.make_disabled(disabled_message)


    def process_load(self):
        return



class GenodeBaseProg(GenodeProg):

    def __init__(self, prog_name, env, build_helper, prog_base_path):

        super().__init__(prog_name, env)

        # for use in sc_tgt_path
        self.relative_src_dir = self.env['fn_localize_path'](prog_base_path)
        self.relative_prog_dir = self.env['fn_localize_path'](os.path.join(env['BUILD'], prog_name))

        self.build_helper = build_helper

        self.env['ent_current_target_alias'] = self.env['fn_prog_alias_name'](self.prog_name)
        self.env['fn_norm_tgt_path'] = lambda tgt: self.norm_tgt_path(tgt)
        self.env['fn_sc_tgt_path'] = lambda tgt: self.sc_tgt_path(tgt)

        self.post_process_actions = []
        self.env['fn_add_post_process_action'] = lambda action: self.post_process_actions.append(action)

        self.rules_handling_skipped = False

        target_cwd = self.norm_tgt_path(None)
        if not os.path.isdir(target_cwd):
            os.makedirs(target_cwd)


    def norm_tgt_path(self, target):
        if target is not None:
            return '%s/%s' % (self.relative_prog_dir, target)
        else:
            return self.relative_prog_dir


    def build_c_objects(self):
        src_files = self.get_c_sources()
        return self.build_helper.compile_c_sources(self.env, src_files)


    def build_cc_objects(self):
        src_files = self.get_cc_sources()
        return self.build_helper.compile_cc_sources(self.env, src_files)


    def build_s_objects(self):
        src_files = self.get_s_sources()
        return self.build_helper.compile_s_sources(self.env, src_files)


    def build_binary_objects(self):
        src_files = self.get_binary_sources()
        return self.build_helper.compile_binary_sources(self.env, src_files)


    def build_o_objects(self):
        # requires custom builder
        return []



class GenodeMkProg(GenodeBaseProg):
    def __init__(self, prog_name, env,
                 prog_mk_file, prog_mk_repo,
                 build_env):

        prog_env = env.Clone()
        self.env = prog_env    # avoid cloning environment again in GenodeTarget

        self.build_env = scmkevaluator.ScMkEnv(prog_env,
                                               mk_cache=build_env.mk_cache,
                                               parent_env=build_env)
        self.prog_mk_file = prog_mk_file
        self.prog_mk_repo = prog_mk_repo
        self.build_env.var_set('REP_DIR', self.prog_mk_repo)

        prog_mk_path = os.path.dirname(prog_mk_file)
        self.build_env.var_set('PRG_DIR', prog_mk_path)

        super().__init__(prog_name, prog_env,
                         genode_build_helper.GenodeMkBuildHelper(self.build_env),
                         prog_mk_path)
        self.build_env.set_relative_targets_dir(self.norm_tgt_path(None))

        self.forced_overlay_type = None


    def disable_overlay(self):
        self.forced_overlay_type = 'no_overlay'


    def enforce_overlay_type(self, forced_overlay_type):
        self.forced_overlay_type = forced_overlay_type


    def process_load(self, skip_rules=False):

        mkcache = self.build_env.get_mk_cache()


        # remember value of rep_inc_dir and reset it to empty; it is
        # important to put those remembered values to end of list
        # after processing locally imported makefiles to preserve
        # sequence of include path like in mk build
        global_rep_inc_dir = self.build_env.var_values('REP_INC_DIR')
        self.build_env.var_set('REP_INC_DIR', '')


        ### handle base-libs.mk
        base_libs_mk_file = '%s/mk/base-libs.mk' % (self.env['BASE_DIR'])
        base_libs_mk = mkcache.get_parsed_mk(base_libs_mk_file)
        base_libs_mk.process(self.build_env)


        ### handle include <prog>.mk
        self.env['fn_info']("Parsing build rules for program '%s' from '%s'" %
                            (self.prog_name, self.env['fn_localize_path'](self.prog_mk_file)))
        # overlays for <prog_mk> are already handled on a different level
        prog_mk = mkcache.get_parsed_mk(self.prog_mk_file,
                                        forced_overlay_type=self.forced_overlay_type)
        prog_mk.process(self.build_env, skip_rules)
        self.rules_handling_skipped = skip_rules


        specs = self.env['SPECS']
        self.env['fn_debug']("SPECS: %s" % (str(specs)))


        requires = self.build_env.var_values('REQUIRES')
        missing_specs = [ req for req in requires if req not in specs ]
        if len(missing_specs) > 0:
            self.env['fn_debug']("Skipping loading dependencies of program '%s' due to missing specs: %s"
                                 % (self.prog_name, ' '.join(missing_specs)))
            self.make_disabled("missing specs: %s" % ' '.join(missing_specs))

            return


        ### direct dependency lib objects
        direct_dep_lib_objs = []

        ### register program dependencies
        orig_dep_libs = self.build_env.var_values('LIBS')
        if len(orig_dep_libs) > 0:
            direct_dep_lib_objs += self.env['fn_require_abis_or_libs'](self, orig_dep_libs)
        direct_dep_libs = orig_dep_libs + []


        ### add dependencies for code coverage
        coverage_enabled = (self.build_env.var_value('COVERAGE') == 'yes')
        if coverage_enabled:
            coverage_dep_libs = ['libgcov']
            direct_dep_lib_objs += self.env['fn_require_abis_or_libs'](self, coverage_dep_libs)
            direct_dep_libs.extend(coverage_dep_libs)


        ### add dependencies for sanitizer
        sanitizer_enabled = (self.build_env.var_value('SANITIZE_UNDEFINED') == 'yes')
        if sanitizer_enabled:
            sanitizer_dep_libs = ['libubsan', 'libsanitizer_common']
            direct_dep_lib_objs += self.env['fn_require_abis_or_libs'](self, sanitizer_dep_libs)
            direct_dep_libs.extend(sanitizer_dep_libs)


        ### check if dependencies are not disabled
        if self.is_disabled():
            self.env['fn_debug']("Skipping processing program '%s' due to disabled dependencies: %s"
                                 % (self.target_name, ' '.join(self.get_disabled_dep_target_names())))
            return


        ### calculate list of library dependencies (recursively complete)
        lib_deps = []
        for dep_lib in direct_dep_libs:
            dep_lib_deps = self.env['fn_get_lib_info'](dep_lib)['lib_deps']
            lib_deps.extend(dep_lib_deps)
        lib_deps = sorted(list(set(lib_deps)))
        self.env['fn_debug']("direct_dep_libs: '%s'" % (str(direct_dep_libs)))
        self.env['fn_debug']("lib_deps: '%s'" % (str(lib_deps)))


        ### calculate library deps
        self.lib_so_deps = []
        self.lib_a_deps = []
        for lib in lib_deps:
            if self.env['fn_get_lib_info'](lib)['type'] == 'a':
                self.lib_a_deps.append(lib)
            else:
                self.lib_so_deps.append(lib)


        ### initial cxx_link_opt
        #
        # NOTE: important to retrieve this value before processing
        #       global.mk as LD_OPT is appended inside but it is
        #       processed here independently
        self.cxx_link_opt = self.build_env.var_values('CXX_LINK_OPT')


        ### handle include global.mk
        global_mk_file = '%s/mk/global.mk' % (self.env['BASE_DIR'])
        global_mk = mkcache.get_parsed_mk(global_mk_file)
        global_mk.process(self.build_env)


        ### handle include import-<lib>.mk files
        # reset CXX_LINK_OPT
        self.build_env.var_set('CXX_LINK_OPT', '')
        for dep_lib in direct_dep_libs:
            dep_lib_import_mk_file, dep_lib_import_mk_repo = tools.find_first(self.env['REPOSITORIES'], 'lib/import/import-%s.mk' % (dep_lib))
            if dep_lib_import_mk_file is not None:
                self.env['fn_info']("Processing import-%s file: %s" %
                                    (dep_lib, self.env['fn_localize_path'](dep_lib_import_mk_file)))
                dep_lib_import_mk = mkcache.get_parsed_mk(dep_lib_import_mk_file)
                dep_lib_import_mk.process(self.build_env)
        self.cxx_link_opt_from_imports = self.build_env.var_values('CXX_LINK_OPT')
        self.env['fn_debug']("cxx_link_opt_from_imports: %s" % (str(self.cxx_link_opt_from_imports)))


        # fix rep_inc_dir content - important to be before processing global.mk
        current_rep_inc_dir = self.build_env.var_values('REP_INC_DIR')
        full_rep_inc_dir = current_rep_inc_dir + global_rep_inc_dir
        #self.env['fn_debug']('full_rep_inc_dir: %s' % (str(full_rep_inc_dir)))
        self.build_env.var_set('REP_INC_DIR', ' '.join(full_rep_inc_dir))
        #self.env['fn_debug']('REP_INC_DIR: %s' % (str(self.build_env.var_values('REP_INC_DIR'))))


        ### handle include global.mk again
        # global.mk has to be processed again due to handling of
        # ALL_INC_DIR which is calculated using HOST_INC_DIR that can
        # be modified in import-<lib>.mk files like in
        # import-syscall-linux.mk. It cannot be processed only after
        # inclusiono of import-<lib>.mk files as values set in it are
        # required in some import-<lib>.mk files like CUSTOM_HOST_CC
        # in import-lx_hybrid.mk
        global_mk.process(self.build_env)


        repositories = self.env['REPOSITORIES']
        self.env['fn_debug']("REPOSITORIES: %s" % (str(repositories)))


        self.env['fn_trace'](pprint.pformat(self.build_env.debug_struct('pretty'), width=200))



    def do_process_target(self):

        repositories = self.env['REPOSITORIES']
        specs = self.env['SPECS']

        ### create links to shared library dependencies
        dep_shlib_links = self.build_helper.create_dep_lib_links(
            self.env, self.sc_tgt_path(None), self.lib_so_deps)


        ### handle ld_opt_nostdlib
        ld_opt_nostdlib = self.build_env.var_values('LD_OPT_NOSTDLIB')
        self.cxx_link_opt += ld_opt_nostdlib


        ### common code

        all_inc_dir = self.build_env.var_values('ALL_INC_DIR')
        all_inc_dir = [ path if os.path.isabs(path) else self.norm_tgt_path(path) for path in all_inc_dir ]
        all_inc_dir = [ path for path in all_inc_dir if os.path.isdir(path) or self.env['fn_localize_path'](path).startswith(self.env['BUILD']) ]
        all_inc_dir = [ self.sconsify_path(path) for path in all_inc_dir ]

        self.env.AppendUnique(CPPPATH=all_inc_dir)
        self.env['fn_debug']('CPPPATH: %s' % (self.env['CPPPATH']))

        self.build_helper.prepare_env(self.env)

        objects = []

        ### handle c compilation
        # $(VERBOSE)$(CC) $(CC_DEF) $(CC_C_OPT) $(INCLUDES) -c $< -o $@

        c_objs = self.build_c_objects()
        objects += c_objs


        ### handle cxx compilation
        # $(VERBOSE)$(CXX) $(CXX_DEF) $(CC_CXX_OPT) $(INCLUDES) -c $< -o $@

        cc_objs = self.build_cc_objects()
        objects += cc_objs
        #self.env['fn_debug']('cc_objs: %s' % (str(cc_objs)))

        s_objs = self.build_s_objects()
        objects += s_objs

        binary_objs = self.build_binary_objects()
        objects += binary_objs

        o_objs = self.build_o_objects()
        objects += o_objs

        # for compatibility with make build (it won't work for special
        # cases like: a.cpp a.bbb.cpp as in make sources are sorted
        # but here object files
        objects = list(sorted(objects, key=lambda x: str(x)))



        ### ld_text_addr
        ld_text_addr = '0x01000000'
        if self.build_env.check_var('LD_TEXT_ADDR'):
            ld_text_addr = self.build_env.var_value('LD_TEXT_ADDR')
        if ld_text_addr != '':
            self.cxx_link_opt.append('-Wl,-Ttext=%s' % (ld_text_addr))


        ### cc_march
        cc_march = self.build_env.var_values('CC_MARCH')
        self.cxx_link_opt.extend(cc_march)


        ### ld_script_static
        ld_script_static = None
        if self.build_env.check_var('LD_SCRIPT_STATIC'):
            ld_script_static = self.build_env.var_values('LD_SCRIPT_STATIC')
        else:
            ld_script_static = ['%s/src/ld/genode.ld' % (self.env['BASE_DIR'])]
            if 'linux' in specs:
                stack_area_ld_file, stack_area_ld_repo = tools.find_first(repositories, 'src/ld/stack_area.ld')
                ld_script_static.append(stack_area_ld_file)


        ### #
        ### # Enforce unconditional call of gnatmake rule when compiling Ada sources
        ### #
        ### # Citation from texinfo manual for make:
        ### #
        ### # If a rule has no prerequisites or commands, and the target of the rule
        ### # is a nonexistent file, then `make' imagines this target to have been
        ### # updated whenever its rule is run.  This implies that all targets
        ### # depending on this one will always have their commands run.
        ### #
        ### FORCE:
        ### $(SRC_ADA:.adb=.o): FORCE
        ###
        ### #
        ### # Run binder if Ada sources are included in the build
        ### #
        ### ifneq ($(SRC_ADS)$(SRC_ADB),)
        ###
        ### CUSTOM_BINDER_FLAGS ?= -n -we -D768k
        ###
        ### OBJECTS += b~$(TARGET).o
        ###
        ### ALIS := $(addsuffix .ali, $(basename $(SRC_ADS) $(SRC_ADB)))
        ### ALI_DIRS := $(foreach LIB,$(LIBS),$(call select_from_repositories,lib/ali/$(LIB)))
        ### BINDER_SEARCH_DIRS = $(addprefix -I$(BUILD_BASE_DIR)/var/libcache/, $(LIBS)) $(addprefix -aO, $(ALI_DIRS))
        ###
        ### BINDER_SRC := b~$(TARGET).ads b~$(TARGET).adb
        ###
        ### $(BINDER_SRC): $(ALIS)
        ### 	$(VERBOSE)$(GNATBIND) $(CUSTOM_BINDER_FLAGS) $(BINDER_SEARCH_DIRS) $(INCLUDES) --RTS=$(ADA_RTS) -o $@ $^
        ### endif

        ld_opt = self.build_env.var_values('LD_OPT')

        ld_scripts = []
        if len(self.lib_so_deps) == 0:
            ld_scripts = self.build_env.var_values('LD_SCRIPT_STATIC')
            pass
        else:
            genode_ld_path = '%s/src/ld/genode_dyn.dl' % (self.env['BASE_DIR'])
            self.env['fn_debug']('genode_ld_path: %s' % (genode_ld_path))
            ld_opt.append('--dynamic-list=%s' % (self.env['fn_localize_path'](genode_ld_path)))
            self.env['fn_debug']('ld_opt: %s' % (str(ld_opt)))
            ld_scripts = self.build_env.var_values('LD_SCRIPT_DYN')

            self.cxx_link_opt.append('-Wl,--dynamic-linker=%s.lib.so' % (self.build_env.var_value('DYNAMIC_LINKER')))
            self.cxx_link_opt.append('-Wl,--eh-frame-hdr')
            self.cxx_link_opt.append('-Wl,-rpath-link=.')

            base_libs = self.build_env.var_values('BASE_LIBS')
            self.lib_a_deps = [ lib for lib in self.lib_a_deps if lib not in base_libs ]

        self.cxx_link_opt.extend(self.cxx_link_opt_from_imports)

        for lib in ld_scripts:
            self.cxx_link_opt += [ '-Wl,-T', '-Wl,%s' % (self.env['fn_localize_path'](lib)) ]

        lib_cache_dir = self.build_helper.get_lib_cache_dir(self.env)
        dep_archives = []
        for dep_lib in self.lib_a_deps:
            a_file_name = '%s.lib.a' % (dep_lib)
            a_path = self.build_helper.target_lib_path(lib_cache_dir, dep_lib, a_file_name)
            dep_archives.append(a_path)
        dep_archives = list(sorted(dep_archives))
        self.env['fn_debug']("dep_archives: %s" % (str(dep_archives)))


        ### handle LD_LIBGCC
        if self.build_env.check_var('LD_LIBGCC'):
            self.env['LD_LIBGCC'] = self.build_env.var_value('LD_LIBGCC')
        else:
            cmd = "%s %s -print-libgcc-file-name" % (self.env['CC'], ' '.join(cc_march)),
            results = subprocess.run(cmd, stdout=subprocess.PIPE,
                                     shell=True, universal_newlines=True, check=True)
            ld_libgcc = results.stdout.strip()
            self.env['LD_LIBGCC'] = ld_libgcc


        prog_targets = []


        ### publish LINK_ITEMS in current env
        # needed e.g. in overlay for base/src/core/target.inc
        self.env['PROG_LINK_ITEMS'] = list(map(str, objects + dep_archives + dep_shlib_links))
        self.env['fn_debug']('PROG_LINK_ITEMS %s' % (str(self.env['PROG_LINK_ITEMS'])))


        if len(objects) > 0:

            self.env['fn_debug']("ld_opt: %s" % (str(ld_opt)))
            self.env['fn_debug']("cxx_link_opt: %s" % (str(self.cxx_link_opt)))

            ext_objects = self.build_env.var_values('EXT_OBJECTS')
            ext_objects = [ os.path.normpath(p) for p in ext_objects ]

            ld_cxx_opt = [ '-Wl,%s' % (opt) for opt in ld_opt ]
            self.env['LINKFLAGS'] = self.cxx_link_opt + ld_cxx_opt
            prog_name = self.build_env.var_value('TARGET')
            ## $LINK -o $TARGET $LINKFLAGS $__RPATH $SOURCES $_LIBDIRFLAGS $_LIBFLAGS
            self.env['LINKCOM'] = '$LINK -o $TARGET $LINKFLAGS $__RPATH -Wl,--whole-archive -Wl,--start-group $SOURCES -Wl,--no-whole-archive -Wl,--end-group $_LIBDIRFLAGS $_LIBFLAGS $LD_LIBGCC'
            prog_tgt = self.env.Program(target=self.sc_tgt_path(prog_name),
                                        source=objects + dep_archives + dep_shlib_links + ext_objects)
            prog_targets.append(prog_tgt)


            debugsyms_tgt = self.env.DebugSymbols(target=self.sc_tgt_path('%s.debug' % (prog_name)),
                                                  source=prog_tgt)
            prog_targets.append(debugsyms_tgt)


            strip_tgt = self.env.Strip(target=self.sc_tgt_path('%s.stripped' % (prog_name)),
                                       source=[prog_tgt, debugsyms_tgt])
            prog_targets.append(strip_tgt)


            # symlink to stripped version
            inst_prog_tgt = self.env.SymLink(source = strip_tgt,
                                             target = self.sconsify_path(os.path.join(self.env['INSTALL_DIR'], prog_name)))
            prog_targets.append(inst_prog_tgt)


            # symlink to debug version
            dbg_prog_tgt = self.env.SymLink(source = strip_tgt,
                                            target = self.sconsify_path(os.path.join(self.env['DEBUG_DIR'], prog_name)))
            prog_targets.append(dbg_prog_tgt)

            # symlink to debug symbols for debug version
            dbg_syms_tgt = self.env.SymLink(source = debugsyms_tgt,
                                            target = self.sconsify_path(os.path.join(self.env['DEBUG_DIR'], '%s.debug' % (prog_name))))
            prog_targets.append(dbg_syms_tgt)


        # handle CONFIG_XSD
        config_xsd = self.build_env.var_value('CONFIG_XSD')
        if len(config_xsd) > 0:
            xsd_name = '%s.xsd' % (prog_name)
            config_xst_tgt = self.env.SymLink(source = os.path.join(self.relative_src_dir, config_xsd),
                                              target=self.sconsify_path(os.path.join(self.env['INSTALL_DIR'], xsd_name)))
            prog_targets.append(config_xst_tgt)


        # handle CUSTOM_TARGET_DEPS
        custom_target_deps = self.build_env.var_values('CUSTOM_TARGET_DEPS')
        for custom_target in custom_target_deps:
            # print(f"custom_target: {str(custom_target)}")
            scons_target_path = self.sc_tgt_path(custom_target)
            sc_tgt_file = self.env['fn_norm_tgt_path'](custom_target)
            # print(f"{sc_tgt_file=}")
            target_rule = self.build_env.get_registered_rule(sc_tgt_file)
            if target_rule is None:
                if self.rules_handling_skipped:
                    self.env['fn_info'](f"Skipping custom target dep {custom_target} for prog with disabled rules")
                    continue
                else:
                    self.env['fn_error'](f"No rule for Custom target dep {custom_target}")
                    continue
                    quit()
            sc_src_files = [self.env['fn_norm_tgt_path'](src) for src in target_rule.prerequisites]
            # print(f"target_rule: {str(target_rule.debug_struct())}")
            rule_commands = self.build_env.get_rule_commands(sc_tgt_file)
            rule_commands = self.polish_rule_commands(rule_commands)
            # print(f"rule_commands: {pprint.pformat(rule_commands)}")

            build_tgt = self.env.Command(
                target=[sc_tgt_file],
                source=sc_src_files,
                action=SCons.Action.Action(rule_commands,
                                           self.env['fn_fmt_out'](sc_tgt_file, 'BUILD', rule_commands)),
            )
            prog_targets.append(build_tgt)


        ## execute post_process_actions
        for action in self.post_process_actions:
            action()

        self.env['fn_debug']('prog_targets: %s' % (str(list(map(str, prog_targets)))))

        retval = self.env.Alias(self.env['fn_prog_alias_name'](self.prog_name), prog_targets)
        self.env['fn_debug']('retval: %s' % (str(list(map(str, retval)))))
        return retval


    msg_command_pattern = re.compile('^@echo -e " *(CONFIG|BUILD) *".*')
    def polish_rule_commands(self, rule_commands):
        # remove MSG_
        def exclude_command(command):
            if re.match(self.msg_command_pattern, command):
                return True
            return False
        rule_commands = [cmd for cmd in rule_commands if not exclude_command(cmd)]

        working_path = self.env['fn_norm_tgt_path'](None)
        rule_commands = [f"cd {working_path} && ({cmd})" for cmd in rule_commands if not exclude_command(cmd)]

        return rule_commands

    def get_sources(self, files):
        src_files = []
        for src_file in files:
            working_path = self.env['fn_norm_tgt_path'](None)
            file_paths = [working_path] + self.build_env.find_vpaths(src_file)
            if src_file.startswith('/'):
                file_paths = [ os.path.dirname(src_file) ]
                src_file = os.path.basename(src_file)
            existing_file_paths = [ f for f in file_paths if self.build_env.is_file_or_target(os.path.join(f, src_file)) ]

            self.env['fn_debug']('get_sources: default %s' % (os.path.join(self.relative_src_dir, src_file)))
            if (len(existing_file_paths) == 0
                and os.path.isfile(os.path.join(self.relative_src_dir, src_file))):
                existing_file_paths += [self.relative_src_dir]

            if len(existing_file_paths) == 0:
                self.env['fn_error']("Expected exactly one vpath for %s but none from %s found" % (src_file, ' '.join(file_paths)))
                quit()
            if len(existing_file_paths) != 1:
                self.env['fn_notice']("Expected exactly one vpath for %s but exist %s from %s found" % (src_file, ' '.join(existing_file_paths), ' '.join(file_paths)))

            src_file_path = self.sconsify_path(existing_file_paths[0])
            src_files.append((src_file_path, src_file))
        return src_files


    def get_c_sources(self):
        src_c = self.build_env.var_values('SRC_C')
        src_files = self.get_sources(src_c)
        return src_files


    def get_cc_sources(self):
        src_cc = self.build_env.var_values('SRC_CC')
        src_files = self.get_sources(src_cc)
        return src_files


    def get_s_sources(self):
        src_s = self.build_env.var_values('SRC_S')
        src_files = self.get_sources(src_s)
        return src_files


    def get_binary_sources(self):
        src_bin = self.build_env.var_values('SRC_BIN')
        src_files = self.get_sources(src_bin)
        return src_files

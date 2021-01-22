
import os
import re
import subprocess

# debug support
import pprint

from gscons import mkevaluator
from gscons import mkparser
from gscons import scmkevaluator

from gscons import genode_build_helper

from gscons import genode_tools as tools


class GenodeProg:

    def __init__(self, prog_name, env, build_helper, prog_base_path):
        self.prog_name = prog_name
        self.env = env

        # for use in sc_tgt_path
        self.relative_src_dir = self.env['fn_localize_path'](prog_base_path)
        self.relative_prog_dir = self.env['fn_localize_path'](os.path.join(env['BUILD'], prog_name))

        self.build_helper = build_helper

        self.env['fn_current_target_type'] = lambda : 'prog'
        self.env['fn_current_target_alias'] = lambda : self.env['fn_prog_alias_name'](self.prog_name)
        self.env['fn_current_target_obj'] = lambda : self
        self.env['fn_norm_tgt_path'] = lambda tgt: self.norm_tgt_path(tgt)
        self.env['fn_sc_tgt_path'] = lambda tgt: self.sc_tgt_path(tgt)

        self.post_process_actions = []
        self.env['fn_add_post_process_action'] = lambda action: self.post_process_actions.append(action)


    def sconsify_path(self, path):
        return self.env['fn_sconsify_path'](path)


    def norm_tgt_path(self, target):
        if target is not None:
            return '%s/%s' % (self.relative_prog_dir, target)
        else:
            return self.relative_prog_dir


    def sc_tgt_path(self, target):
        return self.sconsify_path(self.norm_tgt_path(target))


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



class GenodeMkProg(GenodeProg):
    def __init__(self, prog_name, env,
                 prog_mk_file, prog_mk_repo,
                 build_env):

        prog_env = env.Clone()

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

        self.no_overlay = False


    def disable_overlay(self):
        self.no_overlay = True


    def process(self):

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
        prog_mk = mkcache.get_parsed_mk(self.prog_mk_file, no_overlay=self.no_overlay)
        prog_mk.process(self.build_env)


        specs = self.env['SPECS']
        self.env['fn_debug']("SPECS: %s" % (str(specs)))


        requires = self.build_env.var_values('REQUIRES')
        missing_specs = [ req for req in requires if req not in specs ]
        if len(missing_specs) > 0:
            self.env['fn_info']("Skipping building program '%s' due to missing specs: %s"
                                % (self.prog_name, ' '.join(missing_specs)))
            return self.env.Alias(self.env['fn_prog_alias_name'](self.prog_name), [])


        ### register program dependencies
        orig_dep_libs = self.build_env.var_values('LIBS')
        if len(orig_dep_libs) > 0:
            dep_lib_targets = self.env['fn_require_libs'](orig_dep_libs)
        direct_dep_libs = orig_dep_libs + []


        ### calculate list of library dependencies (recursively complete)
        lib_deps = []
        for dep_lib in direct_dep_libs:
            dep_lib_deps = self.env['fn_get_lib_info'](dep_lib)['lib_deps']
            lib_deps.extend(dep_lib_deps)
        lib_deps = sorted(list(set(lib_deps)))
        self.env['fn_debug']("direct_dep_libs: '%s'" % (str(direct_dep_libs)))
        self.env['fn_debug']("lib_deps: '%s'" % (str(lib_deps)))


        ### calculate library deps
        lib_so_deps = []
        lib_a_deps = []
        for lib in lib_deps:
            if self.env['fn_get_lib_info'](lib)['type'] == 'a':
                lib_a_deps.append(lib)
            else:
                lib_so_deps.append(lib)


        ### create links to shared library dependencies
        dep_shlib_links = self.build_helper.create_dep_lib_links(
            self.env, self.sc_tgt_path(None), lib_so_deps)


        ### initial cxx_link_opt
        #
        # NOTE: important to retrieve this value before processing
        #       global.mk as LD_OPT is appended inside but it is
        #       processed here independently
        cxx_link_opt = self.build_env.var_values('CXX_LINK_OPT')


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
        cxx_link_opt_from_imports = self.build_env.var_values('CXX_LINK_OPT')
        self.env['fn_debug']("cxx_link_opt_from_imports: %s" % (str(cxx_link_opt_from_imports)))


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


        ### handle ld_opt_nostdlib
        ld_opt_nostdlib = self.build_env.var_values('LD_OPT_NOSTDLIB')
        cxx_link_opt += ld_opt_nostdlib



        ### common code

        all_inc_dir = self.build_env.var_values('ALL_INC_DIR')
        all_inc_dir = [ path for path in all_inc_dir if os.path.isdir(path) ]
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
            cxx_link_opt.append('-Wl,-Ttext=%s' % (ld_text_addr))


        ### cc_march
        cc_march = self.build_env.var_values('CC_MARCH')
        cxx_link_opt.extend(cc_march)


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
        if len(lib_so_deps) == 0:
            ld_scripts = self.build_env.var_values('LD_SCRIPT_STATIC')
            pass
        else:
            genode_ld_path = '%s/src/ld/genode_dyn.dl' % (self.env['BASE_DIR'])
            self.env['fn_debug']('genode_ld_path: %s' % (genode_ld_path))
            ld_opt.append('--dynamic-list=%s' % (self.env['fn_localize_path'](genode_ld_path)))
            self.env['fn_debug']('ld_opt: %s' % (str(ld_opt)))
            ld_scripts = self.build_env.var_values('LD_SCRIPT_DYN')

            cxx_link_opt.append('-Wl,--dynamic-linker=%s.lib.so' % (self.build_env.var_value('DYNAMIC_LINKER')))
            cxx_link_opt.append('-Wl,--eh-frame-hdr')
            cxx_link_opt.append('-Wl,-rpath-link=.')

            base_libs = self.build_env.var_values('BASE_LIBS')
            lib_a_deps = [ lib for lib in lib_a_deps if lib not in base_libs ]

        cxx_link_opt.extend(cxx_link_opt_from_imports)

        for lib in ld_scripts:
            cxx_link_opt += [ '-Wl,-T', '-Wl,%s' % (self.env['fn_localize_path'](lib)) ]

        lib_cache_dir = self.build_helper.get_lib_cache_dir(self.env)
        dep_archives = []
        for dep_lib in lib_a_deps:
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
            self.env['fn_debug']("cxx_link_opt: %s" % (str(cxx_link_opt)))

            ext_objects = self.build_env.var_values('EXT_OBJECTS')
            ext_objects = [ os.path.normpath(p) for p in ext_objects ]

            ld_cxx_opt = [ '-Wl,%s' % (opt) for opt in ld_opt ]
            self.env['LINKFLAGS'] = cxx_link_opt + ld_cxx_opt
            prog_name = self.build_env.var_value('TARGET')
            ## $LINK -o $TARGET $LINKFLAGS $__RPATH $SOURCES $_LIBDIRFLAGS $_LIBFLAGS
            self.env['LINKCOM'] = '$LINK -o $TARGET $LINKFLAGS $__RPATH -Wl,--whole-archive -Wl,--start-group $SOURCES -Wl,--no-whole-archive -Wl,--end-group $_LIBDIRFLAGS $_LIBFLAGS $LD_LIBGCC'
            prog_tgt = self.env.Program(target=self.sc_tgt_path(prog_name),
                                        source=objects + dep_archives + dep_shlib_links + ext_objects)
            prog_targets.append(prog_tgt)

            strip_tgt = self.env.Strip(target=self.sc_tgt_path('%s.stripped' % (prog_name)),
                                       source=prog_tgt)
            prog_targets.append(strip_tgt)


            # symlink to stripped version
            inst_prog_tgt = self.env.SymLink(source = strip_tgt,
                                             target = self.sconsify_path(os.path.join(self.env['INSTALL_DIR'], prog_name)))
            prog_targets.append(inst_prog_tgt)


            # symlink to debug version
            dbg_prog_tgt = self.env.SymLink(source = prog_tgt,
                                            target = self.sconsify_path(os.path.join(self.env['DEBUG_DIR'], prog_name)))
            prog_targets.append(dbg_prog_tgt)


        # handle CONFIG_XSD
        config_xsd = self.build_env.var_value('CONFIG_XSD')
        if len(config_xsd) > 0:
            xsd_name = '%s.xsd' % (prog_name)
            config_xst_tgt = self.env.SymLink(source = os.path.join(self.relative_src_dir, config_xsd),
                                              target=self.sconsify_path(os.path.join(self.env['INSTALL_DIR'], xsd_name)))
            prog_targets.append(config_xst_tgt)


        ## execute post_process_actions
        for action in self.post_process_actions:
            action()

        self.env['fn_debug']('prog_targets: %s' % (str(list(map(str, prog_targets)))))

        retval = self.env.Alias(self.env['fn_prog_alias_name'](self.prog_name), prog_targets)
        self.env['fn_debug']('retval: %s' % (str(list(map(str, retval)))))
        return retval


    def get_sources(self, files):
        src_files = []
        for src_file in files:
            file_paths = self.build_env.find_vpaths(src_file)
            if src_file.startswith('/'):
                file_paths = [ os.path.dirname(src_file) ]
                src_file = os.path.basename(src_file)
            existing_file_paths = [ f for f in file_paths if os.path.isfile(os.path.join(f, src_file)) ]

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

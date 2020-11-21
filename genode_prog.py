
import os
import re
import subprocess

# debug support
import pprint

import mkevaluator
import mkparser

import genode_build_helper

import genode_tools as tools


class GenodeProg:

    def __init__(self, prog_name, env, build_helper, prog_base_path):
        self.prog_name = prog_name
        self.env = env.Clone()

        # for use in target_path
        self.relative_src_dir = self.env['fn_localize_path'](prog_base_path)
        self.relative_prog_dir = self.sconsify_path(os.path.join(env['BUILD'], prog_name))

        self.build_helper = build_helper

        self.env['fn_target_path'] = lambda tgt: self.target_path(tgt)


    def sconsify_path(self, path):
        return self.env['fn_sconsify_path'](path)


    def target_path(self, target):
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


    def build_o_objects(self):
        # requires custom builder
        return []



class GenodeMkProg(GenodeProg):
    def __init__(self, prog_name, env,
                 prog_mk_file, prog_mk_repo,
                 build_env):
        self.build_env = mkevaluator.MkEnv(mk_cache=build_env.mk_cache,
                                           parent_env=build_env)
        self.prog_mk_file = prog_mk_file
        self.prog_mk_repo = prog_mk_repo
        self.build_env.var_set('REP_DIR', self.prog_mk_repo)

        prog_mk_path = os.path.dirname(prog_mk_file)
        super().__init__(prog_name, env,
                         genode_build_helper.GenodeMkBuildHelper(self.build_env),
                         prog_mk_path)


    def process(self):
        #import rpdb2
        #rpdb2.start_embedded_debugger('password')

        mkcache = self.build_env.get_mk_cache()

        ### handle base-libs.mk
        base_libs_mk_file = '%s/mk/base-libs.mk' % (self.env['BASE_DIR'])
        base_libs_mk = mkcache.get_parsed_mk(base_libs_mk_file)
        base_libs_mk.process(self.build_env)


        ### handle include <prog>.mk

        self.env['fn_info']("Parsing build rules for program '%s' from '%s'" % (self.prog_name, self.prog_mk_file))
        prog_mk = mkcache.get_parsed_mk(self.prog_mk_file)
        #self.env['fn_debug'](pprint.pformat(prog_mk.debug_struct(), width=180))
        prog_mk.process(self.build_env)
        #self.env['fn_debug'](pprint.pformat(self.build_env.debug_struct('pretty'), width=200))


        ### register program dependencies
        direct_dep_libs = self.build_env.var_values('LIBS')
        if len(direct_dep_libs) > 0:
            dep_lib_targets = self.env['fn_require_libs'](direct_dep_libs)

        ### calculate list of static library dependencies (directo only)
        archives = [ lib for lib in direct_dep_libs if self.env['fn_get_lib_info'](lib)['type'] == 'a' ]
        self.env['fn_debug']("archives: %s" % (str(archives)))


        ### calculate list of shared library dependencies (recursively complete)
        lib_so_deps = []
        for dep_lib in direct_dep_libs:
            dep_lib_so_deps = self.env['fn_get_lib_info'](dep_lib)['so_deps']
            lib_so_deps.extend(dep_lib_so_deps)
        lib_so_deps = sorted(lib_so_deps)

        ### create links to shared library dependencies
        dep_shlib_links = self.build_helper.create_dep_lib_links(
            self.env, self.target_path(None), lib_so_deps)

        ### handle include import-<lib>.mk files
        for dep_lib in direct_dep_libs:
            dep_lib_import_mk_file, dep_lib_import_mk_repo = tools.find_first(self.env['REPOSITORIES'], 'lib/import/import-%s.mk' % (dep_lib))
            if dep_lib_import_mk_file is not None:
                self.env['fn_info']("processing import-%s file: %s" % (dep_lib, dep_lib_import_mk_file))
                dep_lib_import_mk = mkcache.get_parsed_mk(dep_lib_import_mk_file)
                dep_lib_import_mk.process(self.build_env)


        ### skipping $(SPEC_FILES) as they are already included
        #
        # NOTE: passing this option is not documented


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
        #self.env['fn_debug'](pprint.pformat(self.build_env.debug_struct('pretty'), width=200))


        repositories = self.env['REPOSITORIES']
        specs = self.env['SPECS']
        self.env['fn_debug']("REPOSITORIES: %s" % (str(repositories)))
        self.env['fn_debug']("SPECS: %s" % (str(specs)))


        ### handle include generic.mk functionality

        ### handle cc_march
        ld_opt_nostdlib = self.build_env.var_values('LD_OPT_NOSTDLIB')
        cxx_link_opt += ld_opt_nostdlib




        ### common code

        all_inc_dir = self.build_env.var_values('ALL_INC_DIR')
        all_inc_dir = [ path for path in all_inc_dir if os.path.isdir(path) ]
        all_inc_dir = [ self.sconsify_path(path) for path in all_inc_dir ]

        self.env.AppendUnique(CPPPATH=all_inc_dir)
        self.env['fn_debug']('CPPPATH: %s' % (self.env['CPPPATH']))

        self.build_helper.prepare_c_env(self.env)
        self.build_helper.prepare_cc_env(self.env)
        self.build_helper.prepare_s_env(self.env)
        self.build_helper.prepare_ld_env(self.env)
        self.build_helper.prepare_strip_env(self.env)

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
            print('genode_ld_path: %s' % (genode_ld_path))
            ld_opt.append('--dynamic-list=%s' % (self.env['fn_localize_path'](genode_ld_path)))
            print('ld_opt: %s' % (str(ld_opt)))
            ld_scripts = self.build_env.var_values('LD_SCRIPT_DYN')

            cxx_link_opt.append('-Wl,--dynamic-linker=%s.lib.so' % (self.build_env.var_value('DYNAMIC_LINKER')))
            cxx_link_opt.append('-Wl,--eh-frame-hdr')
            cxx_link_opt.append('-Wl,-rpath-link=.')

            base_libs = self.build_env.var_values('BASE_LIBS')
            archives = [ lib for lib in archives if lib not in base_libs ]

        for lib in ld_scripts:
            cxx_link_opt += [ '-Wl,-T', '-Wl,%s' % (self.env['fn_localize_path'](lib)) ]

        lib_cache_dir = self.build_helper.get_lib_cache_dir(self.env)
        dep_static_libs = []
        for dep_lib in archives:
            static_archive_name = '%s.lib.a' % (dep_lib)
            static_archive_path = self.build_helper.target_lib_path(lib_cache_dir, dep_lib, static_archive_name)
            dep_static_libs.append(static_archive_path)
        self.env['fn_debug']("dep_static_libs: %s" % (str(dep_static_libs)))


        ### handle LD_LIBGCC
        cmd = "%s %s -print-libgcc-file-name" % (self.env['CC'], ' '.join(cc_march)),
        results = subprocess.run(cmd, stdout=subprocess.PIPE,
                                 shell=True, universal_newlines=True, check=True)
        ld_libgcc = results.stdout
        self.env['LD_LIBGCC'] = ld_libgcc


        prog_targets = []

        self.env['fn_debug']("ld_opt: %s" % (str(ld_opt)))
        self.env['fn_debug']("cxx_link_opt: %s" % (str(cxx_link_opt)))

        ld_cxx_opt = [ '-Wl,%s' % (opt) for opt in ld_opt ] 
        self.env['LINKFLAGS'] = cxx_link_opt + ld_cxx_opt
        prog_name = self.build_env.var_value('TARGET')
        ## $LINK -o $TARGET $LINKFLAGS $__RPATH $SOURCES $_LIBDIRFLAGS $_LIBFLAGS
        self.env['LINKCOM'] = '$LINK -o $TARGET $LINKFLAGS $__RPATH -Wl,--whole-archive -Wl,--start-group $SOURCES -Wl,--no-whole-archive -Wl,--end-group $_LIBDIRFLAGS $_LIBFLAGS $LD_LIBGCC'
        prog_tgt = self.env.Program(target=self.target_path(prog_name),
                                    source=objects + dep_static_libs + dep_shlib_links)
        prog_targets.append(prog_tgt)

        strip_tgt = self.env.Strip(target=self.target_path('%s.stripped' % (prog_name)),
                                   source=prog_tgt)
        prog_targets.append(strip_tgt)

        self.env['fn_notice']('prog_targets: %s' % (str(list(map(str, prog_targets)))))

        retval = self.env.Alias(self.env['fn_prog_alias_name'](self.prog_name), prog_targets)
        self.env['fn_notice']('retval: %s' % (str(list(map(str, retval)))))
        return retval


    def get_sources(self, files):
        src_files = []
        for src_file in files:
            file_paths = self.build_env.find_vpaths(src_file)
            existing_file_paths = [ f for f in file_paths if os.path.isfile(os.path.join(f, src_file)) ]

            self.env['fn_debug']('get_sources: default %s' % (os.path.join(self.relative_src_dir, src_file)))
            if (len(existing_file_paths) == 0
                and os.path.isfile(os.path.join(self.relative_src_dir, src_file))):
                existing_file_paths += [self.relative_src_dir]

            if len(existing_file_paths) != 1:
                self.env['fn_notice']("expected exactly one vpath for %s but exist %s from %s found" % (src_file, str(existing_file_paths), str(file_paths)))

            src_file = os.path.join(existing_file_paths[0], src_file)
            src_file = self.sconsify_path(src_file)
            src_files.append(src_file)
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


import os

class GenodeBuildHelper:

    def get_lib_cache_dir(self, env):
        return env['fn_sconsify_path'](env['LIB_CACHE_DIR'])


    def target_lib_path(self, lib_cache_dir, lib_name, target):
        return '%s/%s/%s' % (lib_cache_dir, lib_name, target)


    def prepare_env(self, env):
        self.prepare_common_env(env)
        self.prepare_c_env(env)
        self.prepare_cc_env(env)
        self.prepare_s_env(env)
        self.prepare_binary_env(env)
        self.prepare_ld_env(env)
        self.prepare_strip_env(env)


    def split_non_unique_args(self, args):
        nonunique, unique = [], []
        last_was_include = False
        for arg in args:
            if last_was_include or arg == '-include':
                nonunique.append(arg)
                last_was_include = not last_was_include
            else:
                unique.append(arg)
        return nonunique, unique


    def prepare_common_env(self, env):
        raise Exception("prepare_common_env should be overridden")


    def prepare_c_env(self, env):
        # setup CC, CFLAGS
        raise Exception("prepare_c_env should be overridden")


    def prepare_cc_env(self, env):
        # setup CXX, CXXFLAGS
        raise Exception("prepare_cc_env should be overridden")


    def prepare_s_env(self, env):
        # setup ASCOM, ASFLAGS
        raise Exception("prepare_s_env should be overridden")


    def prepare_binary_env(self, env):
        # setup AS, AS_OPT
        raise Exception("prepare_binary_env should be overridden")


    def prepare_ld_env(self, env):
        # setup LD*
        raise Exception("prepare_ld_env should be overridden")


    def compile_c_sources(self, env, src_files):
        return self.generic_compile(env, src_files, 'CFLAGS')


    def compile_cc_sources(self, env, src_files):
        return self.generic_compile(env, src_files, 'CCFLAGS')


    def compile_s_sources(self, env, src_files):
        return self.generic_compile(env, src_files, 'ASFLAGS')


    def compile_binary_sources(self, env, src_files):
        objs = []

        for src_file_info in src_files:
            if isinstance(src_file_info, tuple):
                src_file_path, src_file = src_file_info
            else:
                src_file_path, src_file = os.path.split(src_file_info)
            tgt_file = os.path.basename(src_file)
            tgt_subdir = os.path.dirname(src_file)
            tgt_file = 'binary_%s.o' % (tgt_file)
            if tgt_subdir != '':
                tgt_file = os.path.join(tgt_subdir, tgt_file)
            src_file = src_file_path + '/' + src_file
            env['fn_debug']("src_file: %s, tgt_file: %s" % (src_file, tgt_file))

            obj = env.BinaryObj(source = src_file,
                                target = env['fn_sc_tgt_path'](tgt_file))
            objs += obj
        return objs


    def generic_compile(self, env, src_files, flags_var):
        objs = []

        target_get_opts_fun = lambda tgt: None
        if 'fn_get_target_opts' in env:
            target_get_opts_fun = env['fn_get_target_opts']

        target_modify_opts_fun = None
        if 'fn_modify_target_opts' in env:
            target_modify_opts_fun = env['fn_modify_target_opts']

        for src_file_info in src_files:
            if isinstance(src_file_info, tuple):
                src_file_path, src_file = src_file_info
            else:
                src_file_path, src_file = os.path.split(src_file_info)
            tgt_file = os.path.basename(src_file)
            tgt_subdir = os.path.dirname(src_file)
            tgt_basename = os.path.splitext(tgt_file)[0]
            tgt_file = '%s.o' % (tgt_basename)
            if tgt_subdir != '':
                tgt_file = os.path.join(tgt_subdir, tgt_file)
            full_src_file = src_file_path + '/' + src_file
            env['fn_debug']("full_src_file: %s, tgt_file: %s" % (full_src_file, tgt_file))

            kwargs = {}
            opts = env[flags_var]
            opts_changed = False

            target_opts = target_get_opts_fun(tgt_basename)
            if target_opts is not None:
                opts_changed = True
                opts = target_opts + opts

            if target_modify_opts_fun is not None:
                modified_opts = target_modify_opts_fun(src_file, opts)
                if modified_opts is not None:
                    opts_changed = True
                    opts = modified_opts

            if opts_changed:
                kwargs[flags_var] = opts

            obj = env.SharedObject(source = full_src_file,
                                   target = env['fn_sc_tgt_path'](tgt_file),
                                   **kwargs)
            objs += obj
        return objs

    def create_dep_lib_links(self, env, sc_tgt_path, dep_libs):
        lib_cache_dir = self.get_lib_cache_dir(env)

        dep_lib_links = []
        for dep_lib in dep_libs:
            dep_lib_type = env['fn_get_lib_info'](dep_lib)['type']
            if dep_lib_type == 'a':
                continue
            dep_lib_file_name = '%s.lib.so' % (dep_lib)
            dep_lib_so_file_name = '%s.%s.so' % (dep_lib, 'abi' if dep_lib_type == 'abi' else 'lib')

            dep_lib_lnk_tgt = env.SymLink(
                source = self.target_lib_path(lib_cache_dir, dep_lib, dep_lib_so_file_name),
                target = '%s/%s' % (sc_tgt_path, dep_lib_file_name))
            dep_lib_links.append(dep_lib_lnk_tgt)

        return dep_lib_links


class GenodeMkBuildHelper(GenodeBuildHelper):

    def __init__(self, build_env):
        self.build_env = build_env


    def prepare_common_env(self, env):
        # prepare function to retrieve target specific options
        def get_target_opts(tgt):
            opt_name = 'CC_OPT_' + tgt.replace('.', '_')
            if not self.build_env.check_var(opt_name):
                return None
            opts = self.build_env.var_values(opt_name)
            env['fn_debug']('target_opts: %s - %s' % (tgt, str(opts)))
            return opts
        env['fn_get_target_opts'] = get_target_opts


    def prepare_c_env(self, env):
        env['CC'] = self.build_env.var_value('CC')

        cc_def = self.build_env.var_values('CC_DEF')
        nonunique, unique = self.split_non_unique_args(cc_def)
        env.Append(CFLAGS=nonunique)
        env.AppendUnique(CFLAGS=unique)
        #env['fn_debug']('CFLAGS: %s' % (env['CFLAGS']))

        cc_opt_dep_to_remove = self.build_env.var_value('CC_OPT_DEP')
        cc_c_opt = self.build_env.var_value('CC_C_OPT')
        cc_c_opt = cc_c_opt.replace(cc_opt_dep_to_remove, '')
        env.AppendUnique(CFLAGS=cc_c_opt.split())
        #env['fn_debug']('CFLAGS: %s' % (env['CFLAGS']))


    def prepare_cc_env(self, env):
        env['CXX'] = self.build_env.var_value('CXX')

        cxx_def = self.build_env.var_values('CXX_DEF')
        env.AppendUnique(CXXFLAGS=cxx_def)
        #env['fn_debug']('CXXFLAGS: %s' % (env['CXXFLAGS']))

        cc_opt_dep_to_remove = self.build_env.var_value('CC_OPT_DEP')
        cc_cxx_opt = self.build_env.var_value('CC_CXX_OPT')
        cc_cxx_opt = cc_cxx_opt.replace(cc_opt_dep_to_remove, '')
        env.AppendUnique(CXXFLAGS=cc_cxx_opt.split())
        #env['fn_debug']('CXXFLAGS: %s' % (env['CXXFLAGS']))


    def prepare_s_env(self, env):
        #env['ASCOM'] = '$AS $ASFLAGS -o $TARGET $SOURCES'
        env['ASCOM'] = ('$CC $ASFLAGS $CPPFLAGS $_CPPDEFFLAGS $_CPPINCFLAGS'
                         + ' -c -o $TARGET $SOURCES')

        env.Replace(ASPPFLAGS=['-D__ASSEMBLY__'])

        cc_def = self.build_env.var_values('CC_DEF')
        nonunique, unique = self.split_non_unique_args(cc_def)
        env.Append(ASFLAGS=nonunique)
        env.AppendUnique(ASFLAGS=unique)
        #env['fn_debug']('ASFLAGS: %s' % (env['ASFLAGS']))
        env.Append(ASPPFLAGS=nonunique)
        env.AppendUnique(ASPPFLAGS=unique)
        #env['fn_debug']('ASPPFLAGS: %s' % (env['ASPPFLAGS']))

        cc_opt_dep_to_remove = self.build_env.var_value('CC_OPT_DEP')
        cc_opt = self.build_env.var_value('CC_OPT')
        cc_opt = cc_opt.replace(cc_opt_dep_to_remove, '')
        env.AppendUnique(ASPPFLAGS=cc_opt.split())
        env['fn_debug']('ASPPFLAGS: %s' % (env['ASPPFLAGS']))

        cc_opt_dep_to_remove = self.build_env.var_value('CC_OPT_DEP')
        cc_c_opt = self.build_env.var_value('CC_C_OPT')
        cc_c_opt = cc_c_opt.replace(cc_opt_dep_to_remove, '')
        env.AppendUnique(ASFLAGS=cc_c_opt.split())
        env['fn_debug']('ASFLAGS: %s' % (env['ASFLAGS']))


    def prepare_binary_env(self, env):
        env['AS'] = self.build_env.var_value('AS')
        env['AS_OPT'] = self.build_env.var_value('AS_OPT')


    def prepare_ld_env(self, env):
        env['LD'] = self.build_env.var_value('LD')
        env['NM'] = self.build_env.var_value('NM')
        env['OBJCOPY'] = self.build_env.var_value('OBJCOPY')
        env['RANLIB'] = self.build_env.var_value('RANLIB')
        env['AR'] = self.build_env.var_value('AR')
        env['LIBPREFIX'] = ''
        # NOTICE: reproducible builds require D - so it would be -rcsD
        env['ARFLAGS'] = '-rcs'
        # NOTICE: rm is not needed because scons unlinks target before
        #         build (at least for static libraries)
        # env['ARCOM'] = 'rm -f $TARGET\n$AR $ARFLAGS $TARGET $SOURCES'
        # NOTICE: following disables executing ranlib by scons
        env['RANLIBCOM'] = ""
        env['RANLIBCOMSTR'] = ""
        if self.build_env.check_var('LD_CMD'):
            env['LINK'] = self.build_env.var_value('LD_CMD')


    def prepare_strip_env(self, env):
        env['STRIP'] = self.build_env.var_value('STRIP')

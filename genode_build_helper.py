
import os

class GenodeBuildHelper:


    def prepare_c_env(self, env):
        # setup CC, CFLAGS
        raise Exception("prepare_c_env should be overridden")


    def prepare_cc_env(self, env):
        # setup CXX, CXXFLAGS
        raise Exception("prepare_cc_env should be overridden")


    def prepare_s_env(self, env):
        # setup AS, ASFLAGS
        raise Exception("prepare_s_env should be overridden")


    def prepare_ld_env(self, env):
        # setup LD*
        raise Exception("prepare_ld_env should be overridden")


    def compile_c_sources(self, env, src_files):
        return self.generic_compile(env, src_files)


    def compile_cc_sources(self, env, src_files):
        return self.generic_compile(env, src_files)


    def compile_s_sources(self, env, src_files):
        return self.generic_compile(env, src_files)


    def generic_compile(self, env, src_files):
        objs = []
        for src_file in src_files:
            tgt_file = os.path.basename(src_file)
            tgt_file = '%s.o' % (os.path.splitext(tgt_file)[0])
            print("src_file: %s, tgt_file: %s" % (src_file, tgt_file))
            obj = env.SharedObject(source = src_file,
                                   target = env['fn_target_path'](tgt_file))
            objs += obj
        return objs


class GenodeMkBuildHelper(GenodeBuildHelper):

    def __init__(self, build_env):
        self.build_env = build_env

    def prepare_c_env(self, env):
        env['CC'] = self.build_env.var_value('CC')

        cc_def = self.build_env.var_values('CC_DEF')
        env.AppendUnique(CFLAGS=cc_def)
        #print('CFLAGS: %s' % (env['CFLAGS']))

        cc_opt_dep_to_remove = self.build_env.var_value('CC_OPT_DEP')
        cc_c_opt = self.build_env.var_value('CC_C_OPT')
        cc_c_opt = cc_c_opt.replace(cc_opt_dep_to_remove, '')
        env.AppendUnique(CFLAGS=cc_c_opt.split())
        #print('CFLAGS: %s' % (env['CFLAGS']))


    def prepare_cc_env(self, env):
        env['CXX'] = self.build_env.var_value('CXX')

        cxx_def = self.build_env.var_values('CXX_DEF')
        env.AppendUnique(CXXFLAGS=cxx_def)
        #print('CXXFLAGS: %s' % (env['CXXFLAGS']))

        cc_opt_dep_to_remove = self.build_env.var_value('CC_OPT_DEP')
        cc_cxx_opt = self.build_env.var_value('CC_CXX_OPT')
        cc_cxx_opt = cc_cxx_opt.replace(cc_opt_dep_to_remove, '')
        env.AppendUnique(CXXFLAGS=cc_cxx_opt.split())
        #print('CXXFLAGS: %s' % (env['CXXFLAGS']))


    def prepare_s_env(self, env):
        #env['ASCOM'] = '$AS $ASFLAGS -o $TARGET $SOURCES'
        env['ASCOM'] = ('$CC $ASFLAGS $CPPFLAGS $_CPPDEFFLAGS $_CPPINCFLAGS'
                         + ' -c -o $TARGET $SOURCES')

        env.AppendUnique(ASPPFLAGS=['-D__ASSEMBLY__'])

        cc_def = self.build_env.var_values('CC_DEF')
        env.AppendUnique(ASFLAGS=cc_def)
        #print('ASFLAGS: %s' % (env['ASFLAGS']))

        cc_opt_dep_to_remove = self.build_env.var_value('CC_OPT_DEP')
        cc_c_opt = self.build_env.var_value('CC_C_OPT')
        cc_c_opt = cc_c_opt.replace(cc_opt_dep_to_remove, '')
        env.AppendUnique(ASFLAGS=cc_c_opt.split())
        #print('ASFLAGS: %s' % (env['ASFLAGS']))


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



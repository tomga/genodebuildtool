
import argparse
import pprint
import sqlite3

import schema
import mkevaluator
import mkparser
import mklogparser

import genode_util_mk_functions
genode_util_mk_functions.register_mk_functions(mkevaluator.functionsDict)

###
# parse options
###

argparser = argparse.ArgumentParser("buildtool")
argparser.add_argument('targets', metavar='TARGETS', nargs='+',
                       help='build targets')
opts = argparser.parse_args()
pprint.pprint(opts)


###
# verify/prepare database
###

build_db = sqlite3.connect('buildtool.db')

check_result = schema.db_check_schema(build_db, schema.CURRENT_SCHEMA_VERSION)
print('Check schema result: %s' % ('OK' if check_result else 'EMPTY'))
    
if not check_result:
    print("Preparing schema")
    schema.db_prepare_schema(build_db, schema.CURRENT_SCHEMA_VERSION)

    check_result = schema.db_check_schema(build_db, schema.CURRENT_SCHEMA_VERSION)
    print('Check schema result: %s' % ('OK' if check_result else 'EMPTY'))


###
# parse configuration
###

parser = mkparser.initialize()
mkcache = mkevaluator.MkCache(parser)
build_conf = mkcache.get_parsed_mk('/projects/genode/genode/nbuild/linux/etc/build.conf')

specs_conf = mkcache.get_parsed_mk('/projects/genode/genode/nbuild/linux/etc/specs.conf')

##test_mk = mkcache.get_parsed_mk('/projects/genode/tmp/test.mk')
##pprint.pprint(test_mk.debug_struct(), width=180)
##quit()
#
#base_hw_specs_conf = mkcache.get_parsed_mk('/projects/genode/genode/repos/base-hw/etc/specs.conf')
#pprint.pprint(base_hw_specs_conf.debug_struct(), width=180)

base_global = mkcache.get_parsed_mk('/projects/genode/genode/repos/base/mk/global.mk')
#pprint.pprint(base_global.debug_struct(), width=180)


#!!!rules parsing not available
#libcxx = mkcache.get_parsed_mk('/projects/genode/genode/repos/base/lib/mk/cxx.mk')
#pprint.pprint(libcxx.debug_struct(), width=180)
#
#quit()


#pprint.pprint(parse_result.debug_struct(), width=180)

env = mkevaluator.MkEnv(mkcache)

env.get_create_var('BUILD_BASE_DIR').set_value(mkevaluator.MkRValueExpr.from_values_list(['/projects/genode/genode/nbuild/linux']))

build_conf.process(env)
#pprint.pprint(env.debug_struct('pretty'), width=200)

specs_conf.process(env)
#pprint.pprint(env.debug_struct('pretty'), width=200)

#base_hw_specs_conf.process(env)
#pprint.pprint(env.debug_struct('pretty'), width=200)

base_global.process(env)
pprint.pprint(env.debug_struct('pretty'), width=200)

quit()

#pprint.pprint(env.debug_struct('raw'), width=200)
#pprint.pprint(env.debug_struct('calculated'), width=200)
#pprint.pprint(env.debug_struct('pretty'), width=200)



logparser = mklogparser.initialize()
logparse_result = logparser.parse_file('/projects/genode/logs/20200427_211245_linux_linux.nlog')


import sys
from pprint import PrettyPrinter

class Python2PrettyPrinter(pprint.PrettyPrinter):
    class _fake_short_str(str):
        def __len__(self):
            return 1 if super().__len__() else 0

    def format(self, object, context, maxlevels, level):
        res = super().format(object, context, maxlevels, level)
        if isinstance(object, str):
            return (self._fake_short_str(res[0]), ) + res[1:]
        return res

    from io import StringIO
    assert StringIO().write(_fake_short_str('_' * 1000)) == 1000


Python2PrettyPrinter().pprint(logparse_result)

#pprint.pprint(logparse_result, width=2000)

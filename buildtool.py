
import argparse
import pprint
import sqlite3

import schema
import mkevaluator
import mkparser
import mklogparser


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
build_conf = parser.parse_file('/projects/genode/genode/nbuild/linux/etc/build.conf')
specs_conf = parser.parse_file('/projects/genode/genode/nbuild/linux/etc/specs.conf')

#test_mk = parser.parse_file('/projects/genode/tmp/test.mk')
#pprint.pprint(test_mk.debug_struct(), width=180)
#quit()

base_hw_specs_conf = parser.parse_file('/projects/genode/genode/repos/base-hw/etc/specs.conf')
pprint.pprint(base_hw_specs_conf.debug_struct(), width=180)

base_global = parser.parse_file('/projects/genode/genode/repos/base/mk/global.mk')
pprint.pprint(base_global.debug_struct(), width=180)

quit()

#pprint.pprint(parse_result.debug_struct(), width=180)

env = mkevaluator.MkEnv()
build_conf.process(env)
pprint.pprint(env.debug_struct('pretty'), width=200)
specs_conf.process(env)
pprint.pprint(env.debug_struct('pretty'), width=200)
base_hw_specs_conf.process(env)
pprint.pprint(env.debug_struct('pretty'), width=200)

quit()

#pprint.pprint(env.debug_struct('raw'), width=200)
#pprint.pprint(env.debug_struct('calculated'), width=200)
#pprint.pprint(env.debug_struct('pretty'), width=200)



logparser = mklogparser.initialize()
logparse_result = logparser.parse_file('/projects/genode/logs/20200427_211245_linux_linux.nlog')

pprint.pprint(logparse_result, width=180)

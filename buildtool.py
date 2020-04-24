
import argparse
import pprint
import sqlite3

import schema
import mkparser


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
parse_result = parser.parse_file('/projects/genode/genode/nbuild/linux/etc/build.conf')

pprint.pprint(parse_result, width=180)


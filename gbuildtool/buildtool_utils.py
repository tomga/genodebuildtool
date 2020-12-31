
import pprint
import subprocess
import sys

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


def command_execute(command):
    process = subprocess.Popen('set -o pipefail; ' + command,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               shell=True, universal_newlines=True,
                               executable='/bin/bash')

    # Poll process for new output until finished
    while True:
        nextline = process.stdout.readline()
        if nextline == '' and process.poll() is not None:
            break
        sys.stdout.write(nextline)
        sys.stdout.flush()

    output = process.communicate()[0]
    exit_code = process.wait()

    return exit_code, output

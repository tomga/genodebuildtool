
import os
import re
import subprocess

from gscons import mkevaluator
from gscons import mkparser
from gscons import scmkevaluator

from gscons import genode_build_helper
from gscons import genode_target
from gscons import genode_tools as tools


class GenodeBasePort(genode_target.GenodeTarget):

    def __init__(self, port_name, env):

        self.port_name = port_name
        super().__init__(port_name, 'port', 'PRT', env)


    def port_dir(self):
        assert False, "GenodeBasePort::port_dir() is purely virtual"


    def port_outdated(self):
        assert False, "GenodeBasePort::port_outdated() is purely virtual"


class GenodeDisabledPort(GenodeBasePort):

    def __init__(self, port_name, env, disabled_message):

        super().__init__(port_name, env)

        self.make_disabled(disabled_message)


    def port_dir(self):
        return "disabled_port_%s" % (self.port_name)


    def port_outdated(self):
        return False


    def process_load(self):
        return


class GenodePort(GenodeBasePort):

    def __init__(self, port_name, env,
                 port_file, port_repo):

        super().__init__(port_name, env)

        self.port_file = port_file
        self.port_repo = port_repo
        self.is_outdated = None


    def norm_tgt_path(self, target):
        if target is None:
            target = self.target_name
        return os.path.join(self.env['PORT_LOG_DIR'], target)


    def port_dir(self):
        return self.port_directory


    def port_outdated(self):
        return self.is_outdated


    def process_load(self):

        env = self.env

        with open(self.port_file, "r") as f:
            found_port_hash = f.read().strip()
        env['fn_debug']('found_port_hash: %s' % (found_port_hash))

        self.port_directory = os.path.join(env['GENODE_DIR'], 'contrib',
                                           '%s-%s' % (self.port_name, found_port_hash))
        env['fn_debug']('checking port directory: %s' % (self.port_directory))

        if not os.path.isdir(self.port_directory):
            self.is_outdated = True
            if env['PORT_AUTO_UPDATE']:
                env['fn_info']('port outdated (preparing): %s' % (self.port_name))
                self.prepare_port()
            else:
                env['fn_info']('port outdated: %s' % (self.port_name))
                self.make_disabled('port outdated')
            return

        env['fn_debug']('port current: %s' % (self.port_name))
        self.is_outdated = False


    def prepare_port(self):

        env = self.env

        d = { 'genode_dir': env['GENODE_DIR'],
              'port_name': self.port_name,
              }

        cmd = "{genode_dir}/tool/ports/prepare_port {port_name}"
        cmd = cmd.format(**d)
        cmd = cmd.replace('\n', ' ')
        cmd = ' '.join(cmd.split())
        env['fn_debug']('port_cmd: %s' % (str(cmd)))

        port_cmd = ("mkdir -p %s; %s | tee %s | sed -e 's/^/ | /'"
                    % (env['PORT_LOG_DIR'], cmd, self.norm_tgt_path(None)))

        results = subprocess.run(port_cmd,
                                 shell=True, universal_newlines=True, check=True)
        if results.returncode != 0:
            env['fn_error']("error during preparing port '%s'" % (self.port_name()))
            quit()

        self.is_outdated = False


    def do_process_target(self):

        retval = self.env.Alias(self.env['fn_port_alias_name'](self.port_name), [])
        self.env['fn_debug']('retval: %s' % (str(list(map(str, retval)))))
        return retval

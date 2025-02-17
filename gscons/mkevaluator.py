
import copy
import glob
import os
import pprint
import re
import subprocess
import traceback

from gscons import mkexpr

class MkEnvVar:
    def __init__(self, mode='recursive', value=None):
        assert mode == 'recursive' or mode == 'simple'
        self.mode = mode
        self.value = (MkRValueExpr([]) if value is None else
                      value.parsed_expr() if type(value) == MkRValueExprText else
                      value)

    def soft_clone(self):
        return MkEnvVar(mode=self.mode, value=self.value.soft_clone())

    def is_simply_expanded(self):
        return self.mode == 'simple'

    def is_recursively_expanded(self):
        return self.mode == 'recursive'

    def get_value(self):
        return self.value

    def set_value(self, value):
        self.value = value



class MkEnvRule:
    def __init__(self, targets, prerequisites, commands):
        self.targets = targets
        self.prerequisites = prerequisites
        self.commands = [ cmd.parsed_expr() if type(cmd) == MkRValueExprText else cmd
                          for cmd in commands ]

    def get_commands(self):
        return self.value

    def debug_struct(self):
        return [ self.targets, self.prerequisites,
                 [ x.debug_struct() for x in self.commands ] ]


class MkCache:
    def __init__(self, parser):
        self.parsed_makefiles = {}
        self.parser = parser

    def get_parsed_mk(self, makefile):
        if makefile not in self.parsed_makefiles:
            self.parsed_makefiles[makefile] = self.parser.parse_file(makefile)
        return self.parsed_makefiles[makefile]

    def set_parsed_mk(self, makefile, parsed_makefile):
        self.parsed_makefiles[makefile] = parsed_makefile

    def check_parsed_mk(self, makefile):
        return makefile in self.parsed_makefiles



class MkEnv:
    def __init__(self, mk_cache = None, parent_env = None):
        self.variables = {}
        self.vpaths = [] # list of tupples <pattern_re, path>
        self.mk_cache = mk_cache
        self.parent_env = parent_env
        self.registered_targets = {}
        self.rule_processing_disabled = False
        self.registered_rules = []
        self.relative_targets_dir = None

    def dict(self):
        return self.variables;

    def get_create_var(self, varname):
        if self.check_var(varname):
            found_var = self.get_var(varname)
            if varname in self.variables:
                return found_var

            # it means it is from parent
            cloned_var = found_var.soft_clone()
            self.variables[varname] = cloned_var
            return cloned_var

        self.variables[varname] = MkEnvVar()
        return self.variables[varname]

    def get_var(self, varname):
        if varname in self.variables:
            return self.variables[varname]
        if self.parent_env is not None:
            return self.parent_env.get_var(varname)
        return None

    def set_var(self, varname, varvalue):
        self.variables[varname] = varvalue

    def check_var(self, varname):
        if varname in self.variables:
            return True
        if self.parent_env is not None:
            return self.parent_env.check_var(varname)
        return False


    def log(self, level, message):
        assert level in ['error', 'warning', 'notice', 'info', 'debug', 'trace']
        for line in message.split('\n'):
            print("[%s] %s" % (level, line))


    def get_cwd(self):
        return os.getcwd()


    def process_shell_overrides(self, args):
        return None


    def preprocess_shell_command(self, cmd):
        return cmd


    def debug_struct(self, mode):
        retval = {}
        if self.parent_env is not None:
            retval['___parent___'] = self.parent_env.debug_struct(mode)
        for var in self.variables:
            try:
                if mode == 'raw':
                    retval[var] = self.variables[var].get_value().debug_struct()
                elif mode == 'calculated':
                    retval[var] = MkRValueExpr(self.variables[var].get_value().calculated(self)).debug_struct()
                elif mode == 'pretty':
                    retval[var] = MkRValueExpr(self.variables[var].get_value().calculated(self)).value(self)
                else:
                    raise Exception("Unknown debug_struct mode: '%s'" % (str(mode)))
            except Exception as e:
                print("Error processing debug for '%s' variable (%s)" % (str(var), str(self.variables[var].get_value().debug_struct())))
                traceback.print_exception(None, e, e.__traceback__)
                raise e
        return retval

    def get_mk_cache(self):
        if self.mk_cache is not None:
            return self.mk_cache
        if self.parent_env is not None:
            return self.parent_env.get_mk_cache()
        return None

    def var_values(self, var_name):
        var = self.get_var(var_name)
        if var is None:
            return []
        return var.get_value().values_list(self)

    def var_value(self, var_name):
        var = self.get_var(var_name)
        if var is None:
            return ''
        return var.get_value().value(self)

    def var_set(self, var_name, var_value):
        self.get_create_var(var_name).set_value(MkRValueExpr.from_values_list(var_value.split()))

    def append_vpath(self, pattern, path):
        pattern = pattern.replace('.', r'\.')
        pattern = pattern.replace('%', r'.*')
        re_pattern = "^%s$" % (pattern)
        #print("append_vpath: '%s' %s" % (re_pattern, path))
        self.vpaths.append((re.compile(re_pattern), path))

    def find_vpaths(self, filename):
        retval = []
        for pattern, path in self.vpaths:
            if re.search(pattern, filename) is not None:
                retval.append(path)
        return retval

    def register_target_file(self, file_name, rule = None):
        assert file_name not in self.registered_targets
        self.registered_targets[file_name] = rule

    def is_file_or_target(self, file_name):
        if os.path.isfile(file_name):
            return True

        if file_name in self.registered_targets:
            return True

        return False

    def set_relative_targets_dir(self, relative_targets_dir):
        assert self.relative_targets_dir is None
        self.relative_targets_dir = relative_targets_dir

    def disable_rule_processing(self):
        self.rule_processing_disabled = True
    def enable_rule_processing(self):
        self.rule_processing_disabled = False

    def register_rule(self, rule):
        if self.rule_processing_disabled:
            return
        assert self.relative_targets_dir is not None
        self.registered_rules += [ rule ]
        for target in rule.targets:
            self.register_target_file(os.path.join(self.relative_targets_dir, target), rule)

    def get_registered_rule(self, rule_target):
        if rule_target not in self.registered_targets:
            return None
        return self.registered_targets[rule_target]

    def get_rule_commands(self, rule_target):
        rule = self.get_registered_rule(rule_target)
        if rule is None:
            return None
        rule_commands = [ cmd.value(self) for cmd in rule.commands ]
        return rule_commands


class MkRValue:
    """Base class for make rvalues"""

    def calculate(self, mkenv):
        return [self]

    def compactable(self):
        return False

    def compact_with(self, other):
        raise Exception("Not compactable")

    def values_list(self, mkenv):
        values = []
        for a in list(map(lambda x: x.value().split(), [e for e in self.calculate(mkenv) if e.type() != 'SPC'])):
            values += a
        return values


class MkRValueSpace(MkRValue):

    def __init__(self, text : str = ' '):
        self.text = text

    def type(self) -> str:
        return 'SPC'

    def value(self) -> str:
        return self.text

    def compactable(self) -> bool:
        return True

    def compact_with(self, other) -> MkRValue:
        self.text += other.text
        return self

    def debug_struct(self):
        return self.text



class MkRValueText(MkRValue):
    def __init__(self, text : str):
        self.text = text

    def type(self):
        return 'TXT'

    def value(self):
        return self.text

    def compactable(self):
        return True

    def compact_with(self, other):
        self.text += other.text
        return self

    def debug_struct(self):
        return self.text


class MkRValueVar(MkRValue):
    def __init__(self, var_ident, var_expr = None,
                 brace_open=None, brace_close=None):
        self.var_ident = var_ident
        self.var_expr = var_expr
        self.brace_open = brace_open
        self.brace_close = brace_close
        assert brace_open is None or brace_open == '('
        assert brace_close is None or brace_close == ')'

    def type(self):
        return 'VAR'

    def get_var_name(self, mkenv):
        var_name = self.var_ident.value(mkenv)
        if self.brace_open is not None:
            var_name += self.brace_open
        if self.var_expr is not None:
            var_name += ''.join(self.var_expr.values_list(mkenv))
        if self.brace_close is not None:
            var_name += self.brace_close
        return var_name

    def calculate(self, mkenv):
        var_name = self.get_var_name(mkenv)
        # print(f"MkRValueExpr::calculate: {var_name}")
        if not mkenv.check_var(var_name):
            return []
        rval_expr = copy.deepcopy(mkenv.get_var(var_name))
        return rval_expr.get_value().calculated(mkenv)

    def value(self):
        raise Exception("MkRValueVar should have been calculated")

    def debug_struct(self):
        if self.var_expr is None:
            return ['$'] + self.var_ident.debug_struct()
        else:
            return ([ ['$'] + self.var_ident.debug_struct()]
                    + ([self.brace_open] if self.brace_open is not None else [])
                    + [self.var_expr.debug_struct() ]
                    + ([self.brace_close] if self.brace_close is not None else []))


# possibly needs reimplementation
class MkRValueDollarVar(MkRValueVar):
    pass

functionsDict = {}

# 1 args
def mkfun_basename(mkenv, args):
    return [os.path.splitext(x)[0] for x in args[0]]
functionsDict['basename'] = mkfun_basename

def mkfun_dir(mkenv, args):
    return [os.path.dirname(x) for x in args[0]]
functionsDict['dir'] = mkfun_dir

def mkfun_firstword(mkenv, args):
    return [args[0][0]] if len(args[0]) > 0 else []
functionsDict['firstword'] = mkfun_firstword

def mkfun_lastword(mkenv, args):
    return [args[0][-1]] if len(args[0]) > 0 else []
functionsDict['lastword'] = mkfun_lastword

def mkfun_notdir(mkenv, args):
    return [os.path.basename(x) for x in args[0]]
functionsDict['notdir'] = mkfun_notdir

def mkfun_shell(mkenv, args):
    assert len(args) == 1, "TODO: support shell commands with comma"
    #print("SHELL_start: %s" % (' '.join(args[0])))

    override_output = mkenv.process_shell_overrides(args[0])
    if override_output is not None:
        return override_output.split()

    cwd = mkenv.get_cwd()
    if not os.path.isdir(cwd):
        print("SHELL_cwd: %s" % (cwd))
    cmd = mkenv.preprocess_shell_command(' '.join(args[0]))
    results = subprocess.run(cmd,
                             cwd=cwd,
                             stdout=subprocess.PIPE,
                             shell=True, universal_newlines=True, check=True,
                             executable='/bin/bash')
    output = results.stdout
    #if args[0][0] == 'pwd':
    #    print("SHELL_end: %s" % (str(output.split())))
    return output.split()
functionsDict['shell'] = mkfun_shell

def mkfun_sort(mkenv, args):
    assert len(args) == 1, "TODO: support sorting with comma"
    return list(sorted(list(set(args[0]))))
functionsDict['sort'] = mkfun_sort

def mkfun_wildcard(mkenv, args):
    results = []
    for pattern in args[0]:
        assert pattern.startswith('/'), "TODO: support relative wildcard"
        results.extend(glob.glob(pattern))
    #print("WILDCARD: %s" % (str(results)))
    return results
functionsDict['wildcard'] = mkfun_wildcard

# 2 args
def mkfun_addprefix(mkenv, args):
    results = []
    for value in args[1]:
        if len(args[0]) > 1:
            results.extend(args[0][:-1])
        results.append(args[0][-1] + value)
    #print("ADDPREFIX: '%s' '%s' '%s'" % (str(args[0]), str(args[1]), str(results)))
    return results
functionsDict['addprefix'] = mkfun_addprefix

def mkfun_addsuffix(mkenv, args):
    assert len(args[0]) == 1, "addsuffix: only one suffix allowed"
    return [ v + args[0][0] for v in args[1] ]
functionsDict['addsuffix'] = mkfun_addsuffix

def mkfun_filter(mkenv, args):
    assert '%' not in ''.join(args[0]), "TODO: implement real makefile patterns"
    return [ v for v in args[1] if v in args[0] ]
functionsDict['filter'] = mkfun_filter

def mkfun_filter_out(mkenv, args):
    assert '%' not in ''.join(args[0]), "TODO: implement real makefile patterns"
    return [ v for v in args[1] if v not in args[0] ]
functionsDict['filter-out'] = mkfun_filter_out

def mkfun_findstring(mkenv, args):
    assert len(args[0]) == 1, "findstring: only one string to search for allowed"
    return [ args[0][0] ] if args[0][0] in args[1] else []
functionsDict['findstring'] = mkfun_findstring

# 3 args
def mkfun_patsubst(mkenv, args):
    assert len(args[0]) == 1, "TODO: support pattern with spaces"
    assert len(args[1]) == 1, "TODO: support replacement with spaces"
    assert len([x for x in args[0][0] if x == '%']) <= 1, "TODO: Support paterns that contain more than one % char"
    assert len([x for x in args[1][0] if x == '%']) <= 1, "TODO: Support replacements that contain more than one % char"
    assert len([x for x in args[0][0] if x == '%']) == len([x for x in args[1][0] if x == '%']), "Either both patten and replacement % char or both don't"
    if len([x for x in args[0][0] if x == '%']) == 1:
        pattern = re.compile('^' + args[0][0].replace('%', '(.*)') + '$')
        return [ pattern.sub(args[1][0].replace('%', r'\1'), v) for v in args[2] ]
    else:
        return [ args[1][0] if v == args[0][0] else v for v in args[2] ]
functionsDict['patsubst'] = mkfun_patsubst

def mkfun_subst(mkenv, args):
    assert len(args[0]) == 1, "TODO: support pattern with spaces"
    if len(args[1]) == 0:
        args[1].append('')
    assert len(args[1]) == 1, "TODO: support replacement with spaces"
    return [ v.replace(args[0][0], args[1][0]) for v in args[2] ]
functionsDict['subst'] = mkfun_subst

# 1+ args
def mkfun_call(mkenv, args):
    return functionsDict[args[0][0]](mkenv, args[1:])
functionsDict['call'] = mkfun_call

def mkfun_lastword(mkenv, args):
    return args[-1] if len(args) > 0 else []
functionsDict['lastword'] = mkfun_lastword



class MkRValueFun1(MkRValue):
    def __init__(self, funname : str, arg):
        self.funname = funname.strip()
        self.arg = arg

    def type(self):
        return 'FN1'

    def calculate(self, mkenv):
        arg_value = self.arg.values_list(mkenv)
        args = [arg_value]

        result = None
        if self.funname in functionsDict:
            result = MkRValueExpr.from_values_list(functionsDict[self.funname](mkenv, args))
        else:
            raise Exception("Unknown function1: %s" % (self.funname))

        return result.calculated(mkenv)

    def value(self):
        raise Exception("TODO")

    def debug_struct(self):
        return ['$' + self.funname, self.arg.debug_struct()]



class MkRValueFun2(MkRValue):
    def __init__(self, funname, arg1, arg2):
        self.funname = funname.strip()
        self.arg1 = arg1
        self.arg2 = arg2

    def type(self):
        return 'FN2'

    def calculate(self, mkenv):
        arg1_value = self.arg1.values_list(mkenv)
        arg2_value = self.arg2.values_list(mkenv)
        args = [arg1_value, arg2_value]

        result = None
        if self.funname in functionsDict:
            result = MkRValueExpr.from_values_list(functionsDict[self.funname](mkenv, args))
        else:
            raise Exception("Unknown function2: %s" % (self.funname))

        return result.calculated(mkenv)

    def value(self):
        raise Exception("TODO")

    def debug_struct(self):
        return ['$' + self.funname, self.arg1.debug_struct(), self.arg2.debug_struct()]



class MkRValueFun3(MkRValue):
    def __init__(self, funname, arg1, arg2, arg3):
        self.funname = funname.strip()
        self.arg1 = arg1
        self.arg2 = arg2
        self.arg3 = arg3

    def type(self):
        return 'FN3'

    def calculate(self, mkenv):
        result = None

        if self.funname == 'foreach':
            arg1_value = self.arg1.values_list(mkenv)
            arg2_value = self.arg2.values_list(mkenv)
            wrapenv = MkEnv(parent_env=mkenv)
            varname = arg1_value[0]
            variable = wrapenv.get_create_var(varname)
            result_value = []
            for varvalue in arg2_value:
                variable.set_value(MkRValueExpr.from_values_list([varvalue]))
                result_value += self.arg3.values_list(wrapenv)
            result = MkRValueExpr.from_values_list(result_value)
        else:
            arg1_value = self.arg1.values_list(mkenv)
            arg2_value = self.arg2.values_list(mkenv)
            arg3_value = self.arg3.values_list(mkenv)
            args = [arg1_value, arg2_value, arg3_value]

            if self.funname in functionsDict:
                result = MkRValueExpr.from_values_list(functionsDict[self.funname](mkenv, args))
            else:
                raise Exception("Unknown function3: %s" % (self.funname))

        return result.calculated(mkenv)

    def value(self):
        raise Exception("TODO")

    def debug_struct(self):
        return ['$' + self.funname, self.arg1.debug_struct(), self.arg2.debug_struct(), self.arg3.debug_struct()]



class MkRValueFunAny(MkRValue):
    def __init__(self, funname, args):
        self.funname = funname.strip()
        self.args = args

    def type(self):
        return 'FN?'

    def calculate(self, mkenv):
        args = [arg.values_list(mkenv) for arg in self.args]

        result = None
        if self.funname in functionsDict:
            result = MkRValueExpr.from_values_list(functionsDict[self.funname](mkenv, args))
        else:
            raise Exception("Unknown function?: %s" % (self.funname))

        return result.calculated(mkenv)

    def value(self):
        raise Exception("TODO")

    def debug_struct(self):
        return ['$' + self.funname] + [arg.debug_struct() for arg in self.args]



class MkRValueSubst(MkRValue):
    def __init__(self, var_expr, pattern, substitution):
        self.var_expr = var_expr
        self.pattern = pattern
        self.substitution = substitution

    def type(self):
        return 'SUB'

    def calculate(self, mkenv):
        var_expr_value = self.var_expr.values_list(mkenv)
        pattern_value = self.pattern.values_list(mkenv)
        substitution_value = self.substitution.values_list(mkenv)
        args = [pattern_value, substitution_value, var_expr_value]

        assert len(pattern_value) == 1, "TODO: support pattern with spaces"
        assert len(substitution_value) == 1, "TODO: support replacement with spaces"
        assert len([x for x in pattern_value[0] if x == '%']) <= 1, "TODO: Support paterns that contain more than one % char"
        assert len([x for x in substitution_value[0] if x == '%']) <= 1, "TODO: Support replacements that contain more than one % char"
        assert len([x for x in pattern_value[0] if x == '%']) == len([x for x in substitution_value[0] if x == '%']), "Either both patten and replacement % char or both don't"

        if len([x for x in pattern_value[0] if x == '%']) == 0:
            pattern_value[0] = '%' + pattern_value[0]
            substitution_value[0] = '%' + substitution_value[0]

        pattern = re.compile(pattern_value[0].replace('%', '(.*)'))
        substitution = substitution_value[0].replace('%', r'\1')
        subst_result = [ pattern.sub(substitution, v) for v in var_expr_value ]

        result = MkRValueExpr.from_values_list(subst_result)
        return result.calculated(mkenv)


    def value(self):
        raise Exception("TODO")

    def debug_struct(self):
        return [self.var_expr.debug_struct(), ':',
                self.pattern.debug_struct(), self.substitution.debug_struct()]


expr_parser_instance = None
def expr_parser():
    global expr_parser_instance
    if expr_parser_instance is None:
        expr_parser_instance = mkexpr.initialize()
    return expr_parser_instance

class MkRValueExprText:
    def __init__(self, text):
        self.text = text
        self.comment_mark = None
        self.after_comment_text = ''
        self.is_rule_expression = False
        self.expr = None

    def mark_as_rule_expression(self):
        self.is_rule_expression = True
        return self

    def append_text(self, text):
        if self.comment_mark is None:
            self.text += text
        else:
            self.after_comment_text += text
        self.expr = None
        return self

    def append_comment(self, text):
        assert text[0] == '#'
        if self.comment_mark is None:
            self.comment_mark = text[0]
            self.after_comment_text = text[1:]
        else:
            self.after_comment_text += text
        self.expr = None
        return self

    def join_with(self, expr_text):
        if self.comment_mark is None:
            self.text += expr_text.text
            self.comment_mark = expr_text.comment_mark
            self.after_comment_text = expr_text.after_comment_text
        else:
            self.after_comment_text += expr_text.text
            if expr_text.comment_mark is not None:
                self.after_comment_text += expr_text.comment_mark
                self.after_comment_text += expr_text.after_comment_text
        self.expr = None
        return self

    def parsed_expr(self):
        final_text = self.text
        if self.is_rule_expression and self.comment_mark is not None:
            final_text += self.comment_mark
            final_text += self.after_comment_text
        if self.expr is None:
            stripped_text = final_text.strip(' \t')
            try:
                parse_result = expr_parser().parse(stripped_text)
                assert len(parse_result) >= 1
                self.expr = expr_parser().call_actions(parse_result[0])
            except Exception as e:
                print(f"Exception during parsing expression: {stripped_text}")
                #traceback.print_exception(None, e, e.__traceback__)
                raise e

        return self.expr

    #def append_expr(self, expr):
    #    self.parsed_expr().append_expr(expr)

    def calculated(self, mkenv):
        return self.parsed_expr().calculated(mkenv)

    def compacted(self, parts):
        return self.parsed_expr().compacted(parts)

    def calculate_variables(self, mkenv):
        return self.parsed_expr().calculate_variables(mkenv)

    def value(self, mkenv):
        return self.parsed_expr().value(mkenv)

    def values_list(self, mkenv):
        return self.parsed_expr().values_list(mkenv)

    def debug_struct(self):
        return [self.parsed_expr().debug_struct()]


class MkRValueExpr:
    def __init__(self, parts : list[MkRValue]):
        self.parts = parts

    def soft_clone(self):
        return MkRValueExpr(parts=self.parts[:])

    def append_part(self, part):
        if (len(self.parts) > 0
            and part.compactable()
            and self.parts[-1].type() == part.type()):
            self.parts[-1].compact_with(part)
            return self
        self.parts.append(part)
        return self

    def append_parts(self, parts):
        for part in parts:
            self.append_part(part)
        return self

    def append_expr_parts(self, expr):
        for part in expr.parts:
            self.append_part(part)
        return self

    def append_expr(self, expr):
        if len(self.parts) != 0:
            self.parts += [ MkRValueSpace() ]
        self.parts += expr.parts

    def calculated(self, mkenv):
        retval = []
        for part in self.parts:
            retval += part.calculate(mkenv)
        retval = self.compacted(retval)
        return retval

    def compacted(self, parts):
        retval = []
        for part in parts:
            if (len(retval) > 0
                and retval[-1].type() == part.type()
                and part.compactable()):
                retval[-1].compact_with(part)
            else:
                retval += [ copy.deepcopy(part) ]
        return retval

    def calculate_variables(self, mkenv):
        self.parts = self.calculated(mkenv)

    def value(self, mkenv):
        return "".join(map(lambda x: x.value(), self.calculated(mkenv)))

    def values_list(self, mkenv):
        values = []
        for a in list(map(lambda x: x.value().split(), [e for e in self.calculated(mkenv) if e.type() != 'SPC'])):
            values += a
        return values

    def from_values_list(values_list):
        # Construct r value expression from list of text values
        retval = MkRValueExpr([])
        first = True
        for t in values_list:
            if not first:
                retval.append_part(MkRValueSpace())
            retval.append_part(MkRValueText(t))
            first = False
        return retval

    def debug_struct(self):
        retval = []
        for part in self.parts:
            retval.append(part.debug_struct())
        return retval



class MkCommand:
    """Base class for make commands"""

    def process(self, mkenv):
        pass



class MkScript:
    def __init__(self, cmd):
        self.commands = []
        self.append_command(cmd)

    def append_command(self, cmd):
        if cmd is not None:
            self.commands.append(cmd)
        return self

    def process(self, mkenv, skip_rules=False):
        if skip_rules:
            mkenv.disable_rule_processing()
        for cmd in self.commands:
            try:
                cmd.process(mkenv)
            except Exception as e:
                mkenv.log("error", "Error processing command:")
                mkenv.log("error", "%s" % (str(cmd.debug_struct())))
                traceback.print_exception(None, e, e.__traceback__)
                raise e
        if skip_rules:
            mkenv.enable_rule_processing()

    def debug_struct(self):
        retval = []
        previous_cmd = None
        for cmd in self.commands:
            try:
                # print(str(cmd))
                cmd_struct = cmd.debug_struct()
                if cmd_struct is not None:
                    retval.append(cmd_struct)
            except Exception as e:
                if previous_cmd is None:
                    print("Error processing debug for first command")
                else:
                    print("Error debugging command after:")
                    print("%s" % (str(previous_cmd.debug_struct())))
                traceback.print_exception(None, e, e.__traceback__)
                raise e
            previous_cmd = cmd
        return retval



class MkCmdOper(MkCommand):

    def __init__(self):
        self.rval_var = None
        self.rval_expr = None
        self.export = False

    def set_rval_var(self, rval_var):
        self.rval_var = rval_var
        return self

    def set_rval_expr(self, rval_expr):
        self.rval_expr = rval_expr
        return self

    def set_export(self, export):
        self.export = export
        return self

    def get_lvalue(self, mkenv):
        rval_var = copy.deepcopy(self.rval_var)
        rval_var.calculate_variables(mkenv)
        retval = rval_var.value(mkenv)
        return retval

    def debug_struct(self):
        return ((['export'] if self.export else [])
                + [ self.rval_var.debug_struct(), self.debug_struct_oper(), self.rval_expr.debug_struct() ])



class MkCmdAppend(MkCmdOper):

    def process(self, mkenv):
        var_value = mkenv.get_create_var(self.get_lvalue(mkenv))
        rval_value = copy.deepcopy(self.rval_expr)
        if var_value.is_simply_expanded():
            # using get_var does not influence calculation here
            # because if it wasn't defined earlier it wouldn't be
            # 'simply_expanded'
            rval_value.calculate_variables(mkenv)
        var_value.get_value().append_expr(rval_value.parsed_expr())

    def debug_struct_oper(self):
        return '+='



class MkCmdRecursiveExpandAssign(MkCmdOper):
    def process(self, mkenv):
        rval_value = copy.deepcopy(self.rval_expr)
        mkenv.set_var(self.get_lvalue(mkenv), MkEnvVar('recursive', rval_value))

    def debug_struct_oper(self):
        return '='



class MkCmdSimpleExpandAssign(MkCmdOper):
    def process(self, mkenv):
        rval_value = copy.deepcopy(self.rval_expr)
        rval_value.calculate_variables(mkenv)
        mkenv.set_var(self.get_lvalue(mkenv), MkEnvVar('simple', rval_value))

    def debug_struct_oper(self):
        return ':='



class MkCmdOptAssign(MkCmdOper):
    def process(self, mkenv):
        if mkenv.check_var(self.get_lvalue(mkenv)):
            return
        rval_value = copy.deepcopy(self.rval_expr)
        mkenv.set_var(self.get_lvalue(mkenv), MkEnvVar('recursive', rval_value))

    def debug_struct_oper(self):
        return '?='


class MkCmdExpr(MkCommand):

    def __init__(self, expr):
        self.expr = expr

    def process(self, mkenv):
        expr_values = self.expr.values_list(mkenv)
        # ignoring result - only evaluation matters

    def debug_struct(self):
        return [ self.expr.debug_struct() ]


class MkCmdExport(MkCommand):
    def __init__(self, var, unexport=False):
        self.var = var
        self.unexport = unexport

    def process(self, mkenv):
        pass

    def debug_struct(self):
        return [ 'unexport' if self.unexport else 'export', self.var ]


class MkCmdCond(MkCommand):
    def __init__(self, condition, script_true, script_false):
        self.condition = condition
        self.script_true = script_true
        self.script_false = script_false

    def process(self, mkenv):
        if self.condition.check_cond(mkenv):
            self.script_true.process(mkenv)
        elif self.script_false is not None:
            self.script_false.process(mkenv)

    def debug_struct(self):
        return ([ self.condition.debug_struct(), self.script_true.debug_struct() ]
                + ([ self.script_false.debug_struct() ] if self.script_false is not None else []))


class MkCmdInclude(MkCommand):
    def __init__(self, rval_expr, optional=False):
        self.rval_expr = rval_expr
        self.optional = optional

    def process(self, mkenv):
        includes_list = self.rval_expr.values_list(mkenv)
        for include in includes_list:
            if not os.path.isfile(include):
                if self.optional:
                    #print("MkCmdInclude: skipping not existing optionally included file '%s'" % (include))
                    continue
                raise Exception("MkCmdInclude: '%s' file to include does not exist" % (include))
            include_mk = mkenv.get_mk_cache().get_parsed_mk(include)
            include_mk.process(mkenv)

    def debug_struct(self):
        return ([ "-" if self.optional else "" + "include" ]
                + [ self.rval_expr.debug_struct() ])


class MkCmdVpath(MkCommand):
    def __init__(self, rval_pattern, rval_path):
        self.rval_pattern = rval_pattern
        self.rval_path = rval_path

    def process(self, mkenv):
        rval_path_value = copy.deepcopy(self.rval_path)
        rval_path_value = rval_path_value.value(mkenv)
        mkenv.log("debug", "MkCmdVpath: vpath %s %s" % (str(self.rval_pattern), rval_path_value))
        mkenv.append_vpath(self.rval_pattern, rval_path_value)


    def debug_struct(self):
        return ([ "include" ]
                + [ str(self.rval_pattern) ]
                + [ self.rval_path.debug_struct() ])


class MkCondition:
    """Base class for make conditions"""

    def check_cond(self, mkenv):
        pass


class MkCondDef(MkCondition):
    def __init__(self, var):
        self.var = var

    def debug_struct(self):
        return [ self.debug_struct_oper(), self.var ]


class MkCondIfdef(MkCondDef):
    def check_cond(self, mkenv):
        var_name = self.var.value(mkenv)
        return mkenv.check_var(var_name)

    def debug_struct_oper(self):
        return 'ifdef'


class MkCondIfndef(MkCondDef):
    def check_cond(self, mkenv):
        var_name = self.var.value(mkenv)
        return not mkenv.check_var(var_name)

    def debug_struct_oper(self):
        return 'ifndef'



class MkCondEq(MkCondition):
    def __init__(self, left_expr, right_expr):
        self.left_expr = left_expr
        self.right_expr = right_expr

    def check_cond(self, mkenv):
        left = self.left_expr.value(mkenv)
        right = self.right_expr.value(mkenv)
        return self.check_cond_oper(left, right)


    def debug_struct(self):
        return [ self.debug_struct_oper(),
                 self.left_expr.debug_struct(),
                 self.right_expr.debug_struct() ]


class MkCondIfeq(MkCondEq):
    def check_cond_oper(self, left, right):
        return left == right

    def debug_struct_oper(self):
        return 'ifeq'


class MkCondIfneq(MkCondEq):
    def check_cond_oper(self, left, right):
        return not (left == right)

    def debug_struct_oper(self):
        return 'ifneq'



class MkCmdComment(MkCommand):
    def __init__(self, comment):
        self.comment = comment

    def process(self, mkenv):
        pass

    def debug_struct(self):
        # return [ self.comment ]
        return None


class MkCmdRule(MkCommand):
    def __init__(self, targets, sources):
        self.targets = targets
        self.sources = sources
        self.commands = []

    def append_command(self, command):
        self.commands += [ command ]
        return self

    def process(self, mkenv):
        # mkenv.log('warning', pprint.pformat(self.debug_struct(), width=200))
        targets = self.targets.values_list(mkenv)
        prereqs = self.sources.values_list(mkenv)
        env_rule = MkEnvRule(targets, prereqs, self.commands)
        mkenv.register_rule(env_rule)

    def debug_struct(self):
        return [ self.targets.debug_struct(),
                 self.sources.debug_struct(),
                 [ x.debug_struct() for x in self.commands ] ]


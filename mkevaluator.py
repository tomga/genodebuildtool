
import copy
import os
import subprocess
import traceback


class MkEnvVar:
    def __init__(self, mode='recursive', value=None):
        assert mode == 'recursive' or mode == 'simple'
        self.mode = mode
        self.value = value if value is not None else MkRValueExpr()

    def is_simply_expanded(self):
        return self.mode == 'simple'

    def is_recursively_expanded(self):
        return self.mode == 'recursive'

    def get_value(self):
        return self.value

    def set_value(self, value):
        self.value = value



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
        self.mk_cache = mk_cache
        self.parent_env = parent_env

    def dict(self):
        return self.variables;

    def get_create_var(self, varname):
        if self.check_var(varname):
            return self.get_var(varname)

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

    def debug_struct(self, mode):
        retval = {}
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
        return self.get_var(var_name).get_value().values_list(self)

    def var_value(self, var_name):
        return self.get_var(var_name).get_value().value(self)

    def var_set(self, var_name, var_value):
        self.get_create_var(var_name).set_value(MkRValueExpr.from_values_list(var_value.split()))



class MkRValue:
    """Base class for make rvalues"""

    def calculate(self, mkenv):
        return [self]

    def compactable(self):
        return False

    def compact_with(self, other):
        raise Exception("Not compactable")



class MkRValueSpace(MkRValue):
    def type(self):
        return 'SPC'

    def value(self):
        return ' '

    def compactable(self):
        return True

    def compact_with(self, other):
        pass

    def debug_struct(self):
        return ' '



class MkRValueText(MkRValue):
    def __init__(self, text):
        self.text = text

    def type(self):
        return 'TXT'

    def value(self):
        return self.text

    def compactable(self):
        return True

    def compact_with(self, other):
        self.text += other.text

    def debug_struct(self):
        return self.text



class MkRValueVar(MkRValue):
    def __init__(self, var_ident, var_expr = None):
        self.var_ident = var_ident
        self.var_expr = var_expr

    def type(self):
        return 'VAR'

    def get_var_name(self, mkenv):
        var_name = self.var_ident
        if self.var_expr is not None:
            var_name += ''.join(self.var_expr.calculate(mkenv))
            print("MkRValueVar::calculate[var_expr] '%s'" % (str(var_name)))
        return var_name

    def calculate(self, mkenv):
        var_name = self.get_var_name(mkenv)
        if not mkenv.check_var(var_name):
            return []
        rval_expr = copy.deepcopy(mkenv.get_var(var_name))
        return rval_expr.get_value().calculated(mkenv)

    def value(self):
        raise Exception("MkRValueVar should have been calculated")

    def debug_struct(self):
        if self.var_expr is None:
            return '$' + self.var_ident
        else:
            return [ '$' + self.var_ident, self.var_expr.debug_struct() ]


functionsDict = {}

# 1 args
def mkfun_shell(mkenv, args):
    results = subprocess.run(' '.join(args[0]),
                             stdout=subprocess.PIPE,
                             shell=True, universal_newlines=True, check=True)
    output = results.stdout
    print("SHELL: %s" % (output))
    return output.split()
functionsDict['shell'] = mkfun_shell

# 2 args
def mkfun_addprefix(mkenv, args):
    return [ args[0][0] + v for v in args[1] ]
functionsDict['addprefix'] = mkfun_addprefix

def mkfun_filter(mkenv, args):
    assert '%' not in ''.join(args[0]), "TODO: implement real makefile patterns"
    return [ v for v in args[1] if v in args[0] ]
functionsDict['filter'] = mkfun_filter

def mkfun_filter_out(mkenv, args):
    assert '%' not in ''.join(args[0]), "TODO: implement real makefile patterns"
    return [ v for v in args[1] if v not in args[0] ]
functionsDict['filter-out'] = mkfun_filter_out

# 3 args
def mkfun_subst(mkenv, args):
    assert len(args[0]) == 1, "TODO: support pattern with spaces"
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
    def __init__(self, funname, arg):
        self.funname = funname
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
        self.funname = funname
        self.arg1 = arg1
        self.arg2 = arg2

    def type(self):
        return 'FN2'

    def calculate(self, mkenv):
        arg1_value = self.arg1.values_list(mkenv)
        arg2_value = self.arg2.values_list(mkenv)
        args = [arg1_value, arg2_value]

        print("fun: %s, args: %s" % (str(self.funname), str(args)))

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
        self.funname = funname
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
            print("varname: %s" % (str(varname)))
            variable = wrapenv.get_create_var(varname)
            result_value = []
            for varvalue in arg2_value:
                variable.set_value(MkRValueExpr.from_values_list([varvalue]))
                result_value += self.arg3.values_list(wrapenv)
            print("result: %s" % (str(result_value)))
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
        self.funname = funname
        self.args = args

    def type(self):
        return 'FN?'

    def calculate(self, mkenv):
        args = [arg.values_list(mkenv) for arg in self.args]

        result = None
        if self.funname in functionsDict:
            result = MkRValueExpr.from_values_list(functionsDict[self.funname](mkenv, args))
        else:
            raise Exception("Unknown function1: %s" % (self.funname))

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
        var_value = self.var_expr.calculate(mkenv)

        # print("MkRValueSubst::calculate: %s" % (str(var_value)))
        # TODO: implement

        result = MkRValueExpr.from_values_list([ v + "_TODO_MkRValueSubst" for v in var_value ])

        return result.calculated(mkenv)


    def value(self):
        raise Exception("TODO")

    def debug_struct(self):
        return [self.var_expr.debug_struct(), ':',
                self.pattern.debug_struct(), self.substitution.debug_struct()]



class MkRValueExpr:
    def __init__(self, parts = None):
        self.parts = parts if parts is not None else []

    def append_part(self, part):
        if (len(self.parts) > 0
            and part.compactable()
            and self.parts[-1].type() == part.type()):
            self.parts[-1].compact_with(part)
            return self
        self.parts.append(part)
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
        retval = MkRValueExpr()
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

    def process(self, mkenv):
        for cmd in self.commands:
            try:
                cmd.process(mkenv)
            except AttributeError as e:
                print("Error processing command:")
                print("%s" % (str(cmd.debug_struct())))
                traceback.print_exception(None, e, e.__traceback__)
                raise e

    def debug_struct(self):
        retval = []
        previous_cmd = None
        for cmd in self.commands:
            try:
                print(str(cmd))
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
    def __init__(self, var, rval_expr, export):
        self.var = var
        self.rval_expr = rval_expr
        self.export = export

    def debug_struct(self):
        return ((['export'] if self.export else [])
                + [ self.var, self.debug_struct_oper(), self.rval_expr.debug_struct() ])



class MkCmdAppend(MkCmdOper):

    def process(self, mkenv):
        var_value = mkenv.get_create_var(self.var)
        rval_value = copy.deepcopy(self.rval_expr)
        if var_value.is_simply_expanded():
            # using get_var does not influence calculation here
            # because if it wasn't defined earlier it wouldn't be
            # 'simply_expanded'
            rval_value.calculate_variables(mkenv)
        var_value.get_value().append_expr(rval_value)

    def debug_struct_oper(self):
        return '+='



class MkCmdRecursiveExpandAssign(MkCmdOper):
    def process(self, mkenv):
        rval_value = copy.deepcopy(self.rval_expr)
        mkenv.set_var(self.var, MkEnvVar('recursive', rval_value))

    def debug_struct_oper(self):
        return '='



class MkCmdSimpleExpandAssign(MkCmdOper):
    def process(self, mkenv):
        rval_value = copy.deepcopy(self.rval_expr)
        rval_value.calculate_variables(mkenv)
        mkenv.set_var(self.var, MkEnvVar('simple', rval_value))

    def debug_struct_oper(self):
        return ':='



class MkCmdOptAssign(MkCmdOper):
    def process(self, mkenv):
        if mkenv.check_var(self.var):
            return
        rval_value = copy.deepcopy(self.rval_expr)
        mkenv.set_var(self.var, MkEnvVar('recursive', rval_value))

    def debug_struct_oper(self):
        return '?='



class MkCmdExport(MkCommand):
    def __init__(self, var):
        self.var = var

    def process(self, mkenv):
        pass

    def debug_struct(self):
        return [ 'export', self.var ]


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
                    print("MkCmdInclude: skipping not existing optionally included file '%s'" % (include))
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
        rval_path_value.calculate_variables(mkenv)
        print("TODO: vpath%s %s" % (" (optional)" if self.optional else "", str(rval_value.parts)))


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
        var_name = self.var.get_var_name(mkenv)
        return mkenv.check_var(var_name)

    def debug_struct_oper(self):
        return 'ifdef'


class MkCondIfndef(MkCondDef):
    def check_cond(self, mkenv):
        var_name = self.var.get_var_name(mkenv)
        return not mkenv.check_var(var_name)

    def debug_struct_oper(self):
        return 'ifndef'



class MkCondEq(MkCondition):
    def __init__(self, left_expr, right_expr):
        self.left_expr = left_expr
        self.right_expr = right_expr

    def check_cond(self, mkenv):
        left = self.left_expr.calculated(mkenv)
        right = self.right_expr.calculated(mkenv)
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


class MkCmdExpr(MkCommand):
    def __init__(self, expr):
        self.expr = expr

    def process(self, mkenv):
        pass

    def debug_struct(self):
        return [ self.expr.debug_struct() ]

    
class MkCmdRuleHeader(MkCommand):
    def __init__(self, targets, sources):
        self.targets = targets
        self.sources = sources
        #print("MkCmdRuleHeader: %s %s %s" % (str(targets), str(sources)))

    def process(self, mkenv):
        pass

    def debug_struct(self):
        return [ self.targets.debug_struct(),
                 self.sources.debug_struct() ]

class MkCmdRuleCommand(MkCommand):
    def __init__(self, command_str):
        self.command_str = command_str
        #print("MkCmdRuleCommand: %s" % (str(command_str)))

    def process(self, mkenv):
        pass

    def debug_struct(self):
        return [ self.command_str ]

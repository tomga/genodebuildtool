
import parglare
import pprint
import os

from gscons import mkevaluator

def initialize():
    parser_dir = os.path.dirname(os.path.abspath(__file__))
    file_name = '%s/mkparser.pg' % (parser_dir)
    grammar = parglare.Grammar.from_file(file_name)

    actions = {
        "CmdList": [lambda _, nodes: mkevaluator.MkScript(nodes[0]),
                    lambda _, nodes: nodes[0].append_command(nodes[2]),
                    ],
        "Command": [lambda _, nodes: (mkevaluator.MkCmdAppend(nodes[0][0], nodes[1][3], export=False) if nodes[1][1] == '+=' else
                                      mkevaluator.MkCmdRecursiveExpandAssign(nodes[0][0], nodes[1][3], export=False) if nodes[1][1] == '=' else
                                      mkevaluator.MkCmdSimpleExpandAssign(nodes[0][0], nodes[1][3], export=False) if nodes[1][1] == ':=' else
                                      mkevaluator.MkCmdOptAssign(nodes[0][0], nodes[1][3], export=False) if nodes[1][1] == '?=' else
                                      "Invalid command oper %s" % (nodes[1][1])),
                    lambda _, nodes: (mkevaluator.MkCmdExport(nodes[1][0]) if nodes[2] is None else
                                      mkevaluator.MkCmdAppend(nodes[1][0], nodes[2][3], export=True) if nodes[2][1] == '+=' else
                                      mkevaluator.MkCmdRecursiveExpandAssign(nodes[1][0], nodes[2][3], export=True) if nodes[2][1] == '=' else
                                      mkevaluator.MkCmdSimpleExpandAssign(nodes[1][0], nodes[2][3], export=True) if nodes[2][1] == ':=' else
                                      mkevaluator.MkCmdOptAssign(nodes[1][0], nodes[2][3], export=True) if nodes[2][1] == '?=' else
                                      "Invalid command oper %s" % (nodes[2][1])),
                    lambda _, nodes: (mkevaluator.MkCmdAppend(nodes[0]+nodes[1]+nodes[2]+nodes[3], nodes[5][3], export=False) if nodes[5][1] == '+=' else
                                      mkevaluator.MkCmdRecursiveExpandAssign(nodes[0]+nodes[1]+nodes[2]+nodes[3], nodes[5][3], export=False) if nodes[5][1] == '=' else
                                      mkevaluator.MkCmdSimpleExpandAssign(nodes[0]+nodes[1]+nodes[2]+nodes[3], nodes[5][3], export=False) if nodes[5][1] == ':=' else
                                      mkevaluator.MkCmdOptAssign(nodes[0]+nodes[1]+nodes[2]+nodes[3], nodes[5][3], export=False) if nodes[5][1] == '?=' else
                                      "Invalid command oper %s" % (nodes[5][1])),
                    lambda _, nodes: (mkevaluator.MkCmdExport(nodes[1]+nodes[2]+nodes[3]+nodes[4]) if nodes[6] is None else
                                      mkevaluator.MkCmdAppend(nodes[1]+nodes[2]+nodes[3]+nodes[4], nodes[6][3], export=True) if nodes[6][1] == '+=' else
                                      mkevaluator.MkCmdRecursiveExpandAssign(nodes[1]+nodes[2]+nodes[3]+nodes[4], nodes[6][3], export=True) if nodes[6][1] == '=' else
                                      mkevaluator.MkCmdSimpleExpandAssign(nodes[1]+nodes[2]+nodes[3]+nodes[4], nodes[6][3], export=True) if nodes[6][1] == ':=' else
                                      mkevaluator.MkCmdOptAssign(nodes[1]+nodes[2]+nodes[3]+nodes[4], nodes[6][3], export=True) if nodes[6][1] == '?=' else
                                      "Invalid command oper %s" % (nodes[6][1])),
                    lambda _, nodes: nodes[0],
                    lambda _, nodes: nodes[0],
                    lambda _, nodes: nodes[0],
                    lambda _, nodes: (mkevaluator.MkCmdExpr(nodes[0]) if nodes[1] is None else
                                      mkevaluator.MkCmdRuleHeader(nodes[0], nodes[1][1])),
                    lambda _, nodes: mkevaluator.MkCmdRuleCommand(nodes[0]),
                    lambda _, nodes: None,
                    lambda _, nodes: mkevaluator.MkCmdComment(nodes[0]),
                    ],
        "CmdAssign": [lambda _, nodes: [None, nodes[0], nodes[1], nodes[2]],
                     ],
        "RuleList": [lambda _, nodes: [nodes[0]],
                     lambda _, nodes: nodes[0] + [nodes[1]],
                     ],
        "RuleCommand": [lambda _, nodes: nodes[1],
                        ],
        "CondCmd": [lambda _, nodes: mkevaluator.MkCmdCond(nodes[0], nodes[2], None),
                    lambda _, nodes: mkevaluator.MkCmdCond(nodes[0], nodes[2], nodes[6]),
                    lambda _, nodes: mkevaluator.MkCmdCond(nodes[0], nodes[2], [ nodes[6] ]),
                    ],
        "IncludeCmd": [lambda _, nodes: mkevaluator.MkCmdInclude(nodes[2]),
                       lambda _, nodes: mkevaluator.MkCmdInclude(nodes[2], optional=True),
                      ],
        "VPathCmd": [lambda _, nodes: mkevaluator.MkCmdVpath(nodes[2], nodes[4]),
                    ],
        "WSOPT": [lambda _, nodes: nodes[0],
                  lambda _, nodes: "",
                  ],
        "Condition": [lambda _, nodes: (mkevaluator.MkCondIfdef(nodes[2]) if nodes[0] == 'ifdef' else
                                        mkevaluator.MkCondIfndef(nodes[2]) if nodes[0] == 'ifndef' else
                                        "Invalid conditional oper %s" % (nodes[0])),
                      lambda _, nodes: (mkevaluator.MkCondIfeq(nodes[3], nodes[5]) if nodes[0] == 'ifeq' else
                                        mkevaluator.MkCondIfneq(nodes[3], nodes[5]) if nodes[0] == 'ifneq' else
                                        "Invalid conditional oper %s" % (nodes[0])),
                      ],
        "OptRValueExpr": [lambda _, nodes: nodes[0],
                          lambda _, nodes: mkevaluator.MkRValueExpr([]),
                          ],
        "RValueExpr": [lambda _, nodes: mkevaluator.MkRValueExpr([nodes[0]]),
                       lambda _, nodes: nodes[0].append_part(nodes[1]),
                       lambda _, nodes: nodes[0].append_part(mkevaluator.MkRValueSpace()),
                      ],
        "RValuePart": [lambda _, nodes: nodes[0],
                       lambda _, nodes: nodes[0],
                      ],
        "RValuePartExpr": [lambda _, nodes: nodes[1],
                           lambda _, nodes: mkevaluator.MkRValueFun1(nodes[2], nodes[4]),
                           lambda _, nodes: mkevaluator.MkRValueFun2(nodes[2], nodes[4], nodes[6]),
                           lambda _, nodes: mkevaluator.MkRValueFun3(nodes[2], nodes[4], nodes[6], nodes[8]),
                           lambda _, nodes: mkevaluator.MkRValueFunAny(nodes[2], nodes[4]),
                           lambda _, nodes: nodes[2],
                           lambda _, nodes: mkevaluator.MkRValueVar(nodes[2]),
                           lambda _, nodes: mkevaluator.MkRValueVar(nodes[2]),
                           lambda _, nodes: mkevaluator.MkRValueSubst(nodes[2], mkevaluator.MkRValueExpr([]), nodes[4]),
                           lambda _, nodes: mkevaluator.MkRValueSubst(nodes[2], nodes[4], nodes[6]),
                          ],
        "ParamExpr": [lambda _, nodes: mkevaluator.MkRValueExpr([nodes[0]]),
                      lambda _, nodes: nodes[0].append_part(nodes[1]),
                      lambda _, nodes: nodes[0].append_part(mkevaluator.MkRValueSpace()),
                      lambda _, nodes: mkevaluator.MkRValueExpr([]),
                     ],
        "ParamPart": [lambda _, nodes: nodes[0],
                      lambda _, nodes: nodes[0],
                     ],
        "ParamPartExpr": [lambda _, nodes: nodes[1],
                          lambda _, nodes: mkevaluator.MkRValueFun1(nodes[2], nodes[4]),
                          lambda _, nodes: mkevaluator.MkRValueFun2(nodes[2], nodes[4], nodes[6]),
                          lambda _, nodes: mkevaluator.MkRValueFun3(nodes[2], nodes[4], nodes[6], nodes[8]),
                          lambda _, nodes: mkevaluator.MkRValueFunAny(nodes[2], nodes[4]),
                          lambda _, nodes: nodes[2],
                          lambda _, nodes: mkevaluator.MkRValueVar(nodes[2]),
                          lambda _, nodes: mkevaluator.MkRValueVar(nodes[2]),
                          lambda _, nodes: mkevaluator.MkRValueSubst(nodes[2], mkevaluator.MkRValueExpr([]), nodes[4]),
                          lambda _, nodes: mkevaluator.MkRValueSubst(nodes[2], nodes[4], nodes[6]),
                         ],
        "ParamList": [lambda _, nodes: [nodes[0]],
                      lambda _, nodes: nodes[0] + [nodes[2]],
                    ],
        "VarName": [lambda _, nodes: mkevaluator.MkRValueVar(nodes[0]),
                    lambda _, nodes: mkevaluator.MkRValueVar(nodes[0], nodes[1]),
                    lambda _, nodes: mkevaluator.MkRValueVar(nodes[0], nodes[2], nodes[1], nodes[3]),
                   ],
        "RValuePartText": [lambda _, nodes: mkevaluator.MkRValueText(nodes[0]),
                           lambda _, nodes: mkevaluator.MkRValueText(nodes[0]),
                           lambda _, nodes: mkevaluator.MkRValueText(nodes[0][2]),
                           lambda _, nodes: mkevaluator.MkRValueText(nodes[0][1]),
                           lambda _, nodes: mkevaluator.MkRValueText(nodes[0][0] + (nodes[0][1] if nodes[0][1] is not None else "")),
                           lambda _, nodes: mkevaluator.MkRValueText(nodes[0]),
                           lambda _, nodes: mkevaluator.MkRValueText(nodes[0]),
                           lambda _, nodes: mkevaluator.MkRValueText(nodes[0]),
                           lambda _, nodes: mkevaluator.MkRValueText(nodes[0]),
                           lambda _, nodes: mkevaluator.MkRValueSpace(),
                          ],
        "ParamPartText": [lambda _, nodes: mkevaluator.MkRValueText(nodes[0]),
                          lambda _, nodes: mkevaluator.MkRValueText(nodes[0]),
                          lambda _, nodes: mkevaluator.MkRValueText(nodes[0][2]),
                          lambda _, nodes: mkevaluator.MkRValueText(nodes[0][1]),
                          lambda _, nodes: mkevaluator.MkRValueText(nodes[0][0] + (nodes[0][1] if nodes[0][1] is not None else "")),
                          lambda _, nodes: mkevaluator.MkRValueText(nodes[0]),
                          lambda _, nodes: mkevaluator.MkRValueText(nodes[0]),
                          lambda _, nodes: mkevaluator.MkRValueText(nodes[0]),
                          lambda _, nodes: mkevaluator.MkRValueSpace(),
                          ],
        "VarIdentStd": [lambda _, nodes: nodes[0],
                        lambda _, nodes: nodes[0] + nodes[1],
                        lambda _, nodes: nodes[0] + nodes[1],
                        ],
        "Text": [lambda _, nodes: nodes[0],
                 lambda _, nodes: nodes[0],
                 lambda _, nodes: nodes[0] + nodes[1],
                 lambda _, nodes: nodes[0] + nodes[1],
                 ],
        }
    
    parser = parglare.Parser(grammar, ws='\r', actions=actions, debug=False)
    return parser

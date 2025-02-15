
import parglare
import pprint
import os

from gscons import mkevaluator

def initialize():
    parser_dir = os.path.dirname(os.path.abspath(__file__))
    file_name = '%s/mkexpr.pg' % (parser_dir)
    grammar = parglare.Grammar.from_file(file_name)

    actions = {
        # MkRValueExpr
        "OptValueExpr": [lambda _, nodes: nodes[1],
                         lambda _, nodes: mkevaluator.MkRValueExpr([]),
                         ],
        # MkRValueExpr
        "ValueExpr": [lambda _, nodes: mkevaluator.MkRValueExpr(nodes[0]),
                      lambda _, nodes: nodes[0].append_parts(nodes[1]),
                      ],
        # list[MkRValue]
        "ValuePartList": [lambda _, nodes: [ nodes[0] ], # ValuePartText
                          lambda _, nodes: [ nodes[0] ], # ValuePartExpr
                          lambda _, nodes: [ mkevaluator.MkRValueText(nodes[0]) ], # COMMA
                          lambda _, nodes: [ mkevaluator.MkRValueText(nodes[0]) ], # BRACE_OPEN
                          lambda _, nodes: [ mkevaluator.MkRValueText(nodes[0]) ], # BRACE_CLOSE
                          lambda _, nodes: nodes[0] + [ nodes[1], nodes[2] ],
                          lambda _, nodes: nodes[0] + [ nodes[1], nodes[2] ],
                          lambda _, nodes: nodes[0] + [ nodes[1], mkevaluator.MkRValueText(nodes[2]) ],
                          lambda _, nodes: nodes[0] + [ nodes[1], mkevaluator.MkRValueText(nodes[2]) ],
                          lambda _, nodes: nodes[0] + [ nodes[1], mkevaluator.MkRValueText(nodes[2]) ],
                         ],
        # MkRValue (MkRValueText)
        "ValuePartText": [lambda _, nodes: mkevaluator.MkRValueText(nodes[0]),
                          lambda _, nodes: mkevaluator.MkRValueText(nodes[0]),
                         ],
        # MkRValue
        "ValuePartExpr": [lambda _, nodes: mkevaluator.MkRValueDollarVar(mkevaluator.MkRValueExpr([mkevaluator.MkRValueText(nodes[1])])),
                          lambda _, nodes: mkevaluator.MkRValueText(nodes[1]),
                          lambda _, nodes: mkevaluator.MkRValueFun1(nodes[2], nodes[4]),
                          lambda _, nodes: mkevaluator.MkRValueFun2(nodes[2], nodes[4], nodes[6]),
                          lambda _, nodes: mkevaluator.MkRValueFun3(nodes[2], nodes[4], nodes[6], nodes[8]),
                          lambda _, nodes: mkevaluator.MkRValueFunAny(nodes[2], nodes[4]),
                          lambda _, nodes: mkevaluator.MkRValueVar(nodes[2]),
                         ],
        # list[MkRValueExpr]
        "LimitedValueExprList": [lambda _, nodes: [ nodes[0] ],
                                 lambda _, nodes: nodes[0] + [ nodes[2] ],
                                 ],
        # MkRValueExpr
        "LimitedValueExpr": [lambda _, nodes: mkevaluator.MkRValueExpr(nodes[0]),
                             lambda _, nodes: nodes[0].append_parts(nodes[1]),
                             lambda _, nodes: (nodes[0]
                                               .append_part(mkevaluator.MkRValueText(nodes[1]))
                                               .append_parts([ nodes[2] ] if nodes[2] is not None else [])
                                               .append_expr_parts(nodes[3])
                                               .append_parts([ nodes[4] ] if nodes[4] is not None else [])
                                               .append_part(mkevaluator.MkRValueText(nodes[5]))),
                             ],
        # list[MkRValue]
        "LimitedValuePartList": [lambda _, nodes: [ nodes[0] ], # ValuePartText
                                 lambda _, nodes: [ nodes[0] ], # ValuePartExpr
                                 lambda _, nodes: nodes[0] + [ nodes[1], nodes[2] ],
                                 lambda _, nodes: nodes[0] + [ nodes[1], nodes[2] ],
                                 ],
        # MkRValueExpr
        "NoBlankValueExpr": [lambda _, nodes: mkevaluator.MkRValueExpr(nodes[0]),
                             lambda _, nodes: nodes[0].append_parts(nodes[1]),
                             lambda _, nodes: (nodes[0]
                                               .append_part(mkevaluator.MkRValueText(nodes[1]))
                                               .append_parts([ nodes[2] ] if nodes[2] is not None else [])
                                               .append_expr_parts(nodes[3])
                                               .append_parts([ nodes[4] ] if nodes[4] is not None else [])
                                               .append_part(mkevaluator.MkRValueText(nodes[5]))),
                             ],
        # list[MkRValue]
        "NoBlankValuePartList": [lambda _, nodes: [ nodes[0] ], # ValuePartText
                                 lambda _, nodes: [ nodes[0] ], # ValuePartExpr
                                 ],
        # MkRValue (MkRValueSpace)
        "Blank": [lambda _, nodes: mkevaluator.MkRValueSpace(nodes[0]),
                  lambda _, nodes: mkevaluator.MkRValueSpace(nodes[0]),
                  lambda _, nodes: mkevaluator.MkRValueSpace(' '),
                  lambda _, nodes: nodes[0].compact_with(mkevaluator.MkRValueSpace(nodes[1])),
                  lambda _, nodes: nodes[0].compact_with(mkevaluator.MkRValueSpace(nodes[1])),
                  lambda _, nodes: nodes[0].compact_with(mkevaluator.MkRValueSpace(' ')),
                  ],
        }

    parser = parglare.GLRParser(grammar, ws='\r', actions=actions, debug=False)
    # parser = parglare.GLRParser(grammar, ws='\r', debug=False)
    # parser = parglare.GLRParser(grammar, ws='\r', debug=True)
    return parser

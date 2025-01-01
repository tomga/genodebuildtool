
import parglare
import pprint
import os

from gscons import mkevaluator

def initialize():
    parser_dir = os.path.dirname(os.path.abspath(__file__))
    file_name = '%s/mkexpr.pg' % (parser_dir)
    grammar = parglare.Grammar.from_file(file_name)

    actions = {
        "OptValueExpr": [lambda _, nodes: nodes[0],
                         lambda _, nodes: mkevaluator.MkRValueExpr([]),
                         ],
        "ValueExpr": [lambda _, nodes: mkevaluator.MkRValueExpr([nodes[0]]),
                      lambda _, nodes: nodes[0].append_part(nodes[1]),
                      lambda _, nodes: nodes[0].append_part(mkevaluator.MkRValueText(nodes[1])).append_expr_parts(nodes[2]).append_part(mkevaluator.MkRValueText(nodes[3])),
                      lambda _, nodes: nodes[0].append_part(mkevaluator.MkRValueSpace(nodes[1])).append_part(nodes[2]),
                      ],
        "NoCommaValueExpr": [lambda _, nodes: mkevaluator.MkRValueExpr([nodes[0]]),
                             lambda _, nodes: nodes[0].append_part(nodes[1]),
                             lambda _, nodes: nodes[0].append_part(mkevaluator.MkRValueText(nodes[1])).append_expr_parts(nodes[2]).append_part(mkevaluator.MkRValueText(nodes[3])),
                             lambda _, nodes: nodes[0].append_part(mkevaluator.MkRValueSpace(nodes[1])).append_part(nodes[2]),
                             ],
        "ValuePart": [lambda _, nodes: nodes[0],
                      lambda _, nodes: mkevaluator.MkRValueText(nodes[0]),
                     ],
        "NoCommaValuePart": [lambda _, nodes: nodes[0],
                             lambda _, nodes: nodes[0],
                             ],
        "ValuePartExpr": [lambda _, nodes: mkevaluator.MkRValueDollarVar(mkevaluator.MkRValueExpr([mkevaluator.MkRValueText(nodes[1])])),
                          lambda _, nodes: mkevaluator.MkRValueText(nodes[1]),
                          lambda _, nodes: mkevaluator.MkRValueFun1(nodes[2], nodes[4]),
                          lambda _, nodes: mkevaluator.MkRValueFun2(nodes[2], nodes[4], nodes[6]),
                          lambda _, nodes: mkevaluator.MkRValueFun3(nodes[2], nodes[4], nodes[6], nodes[8]),
                          lambda _, nodes: mkevaluator.MkRValueFunAny(nodes[2], nodes[4]),
                          lambda _, nodes: mkevaluator.MkRValueVar(nodes[2]),
                         ],
        "ValueExprList": [lambda _, nodes: [nodes[0]],
                          lambda _, nodes: nodes[0] + [nodes[2]],
                          ],
        "ValuePartText": [lambda _, nodes: mkevaluator.MkRValueText(nodes[0]),
                          lambda _, nodes: mkevaluator.MkRValueText(nodes[0]),
                          lambda _, nodes: mkevaluator.MkRValueSpace(' '),
                         ],
        }

    parser = parglare.Parser(grammar, ws='\r', actions=actions, debug=False)
    # parser = parglare.Parser(grammar, ws='\r', debug=False)
    # parser = parglare.Parser(grammar, ws='\r', debug=True)
    return parser


import os
import parglare
import pprint

from logprocessor import *


def initialize():
    parser_dir = os.path.dirname(os.path.abspath(__file__))
    file_name = '%s/sclogparser.pg' % (parser_dir)
    grammar = parglare.Grammar.from_file(file_name)

    actions = {
        "FullLog": [lambda _, nodes: nodes[7] ],
        "CmdList": [lambda _, nodes: BuildCommandGroup(None, None, '.',
                                                       [ nodes[0] ]  if nodes[0] is not None else []),
                    lambda _, nodes: nodes[0].append(nodes[1]) if nodes[1] is not None else nodes[0],
                    ],
        "Command": [lambda _, nodes: SimpleBuildCommand(nodes[0][0], nodes[0][1], nodes[1]),
                    lambda _, nodes: SimpleBuildCommand(None, None, nodes[0]),
                    lambda _, nodes: None,
                    lambda _, nodes: None,
                    ],

        "BuildCommandTitle": [lambda _, nodes: [ nodes[0].strip(), nodes[2] ] ],

        "SimpleCommandList": [lambda _, nodes: [ nodes[0] ],
                              lambda _, nodes: nodes[0] + [ nodes[1] ],
                              ],
        "SimpleCommand": [lambda _, nodes: nodes[0] ],

        "SimpleCommandText": [lambda _, nodes: nodes[0],
                              lambda _, nodes: nodes[0] + nodes[1],
                    ],
        "SimpleCommandPart": [lambda _, nodes: nodes[0],
                              lambda _, nodes: nodes[0],
                              lambda _, nodes: ' ',
                    ],
        }

    parser = parglare.Parser(grammar, ws='\r', actions=actions)
    return parser

from single_cell_parser.cell_parser import CellParser
from .context import h, fname

def test_cell_parser():
    testParser = CellParser(fname)
    testParser.spatialgraph_to_cell(parameters=None)
    testParser.insert_passive_membrane('Soma')
    testParser.insert_passive_membrane('Dendrite')
    testParser.insert_passive_membrane('ApicalDendrite')
    testParser.insert_hh_membrane('Soma')
    testParser.insert_hh_membrane('Dendrite')
    testParser.insert_hh_membrane('ApicalDendrite')
    for label in list(testParser.cell.branches.keys()):
        for branch in testParser.cell.branches[label]:
            for sec in branch:
                h.psection(sec=sec)
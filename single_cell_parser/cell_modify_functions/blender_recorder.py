from blenderspike_py import CellRecorder

def blender_recorder(cell):
    cell.recording = CellRecorder([sec for sec in cell.sections])
    return cell
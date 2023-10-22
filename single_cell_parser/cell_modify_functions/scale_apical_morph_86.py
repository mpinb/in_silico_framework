import logging

log = logging.getLogger("ISF").getChild(__name__)


def scale_apical_morph_86(cell):
    '''
    This is the method, robert has used for scaling the apical dendrite of CDK morphology 86
    
    scale apical diameters depending on
    distance to soma; therefore only possible
    after creating complete cell
    '''
    import neuron
    h = neuron.h
    dendScale = 2.5
    scaleCount = 0
    for sec in cell.sections:
        if sec.label == 'ApicalDendrite':
            dist = cell.distance_to_soma(sec, 1.0)
            if dist > 1000.0:
                continue
#            for cell 86:
            if scaleCount > 32:
                break
            scaleCount += 1
            #            dummy = h.pt3dclear(sec=sec)
            for i in range(sec.nrOfPts):
                oldDiam = sec.diamList[i]
                newDiam = dendScale * oldDiam
                h.pt3dchange(i, newDiam, sec=sec)


#                x, y, z = sec.pts[i]
#                sec.diamList[i] = sec.diamList[i]*dendScale
#                d = sec.diamList[i]
#                dummy = h.pt3dadd(x, y, z, d, sec=sec)

    log.info('Scaled {:d} apical sections...'.format(scaleCount))
    return cell
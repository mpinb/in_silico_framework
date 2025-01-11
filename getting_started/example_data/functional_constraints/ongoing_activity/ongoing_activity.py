'''Ongoing activity L2 neuron model

'''

import sys
import time
import os, os.path
import glob
import neuron
import single_cell_parser as scp
import single_cell_parser.analyze as sca
import numpy as np
import matplotlib.pyplot as plt
h = neuron.h

__author__ = 'Robert Egger'
__date__ = '2013-01-28'


def ongoing_activity(simName, cellName, evokedUpParamName):
    '''
    pre-stimulus ongoing activity
    '''
    neuronParameters = scp.build_parameters(cellName)
    evokedUpNWParameters = scp.build_parameters(evokedUpParamName)
    scp.load_NMODL_parameters(neuronParameters)
    scp.load_NMODL_parameters(evokedUpNWParameters)
    cellParam = neuronParameters.neuron
    paramEvokedUp = evokedUpNWParameters.network

    #    cell = scp.create_cell(cellParam, scaleFunc=scale_apical)
    cell = scp.create_cell(cellParam)

    uniqueID = str(os.getpid())
    dirName = 'results/'
    dirName += simName
    if not simName.endswith('/'):
        dirName += '/'
    dirName += time.strftime('%Y%m%d-%H%M')
    if not os.path.exists(dirName):
        os.makedirs(dirName)

    vTraces = []
    tTraces = []
    recordingSiteFiles = neuronParameters.sim.recordingSites
    recSiteManagers = []
    for recFile in recordingSiteFiles:
        recSiteManagers.append(sca.RecordingSiteManager(recFile, cell))

#    nSweeps = 2000
    nSweeps = 10
    tOffset = 0.0  # avoid numerical transients
    tStop = 1200.0
    #    tStop = 600.0
    neuronParameters.sim.tStop = tStop
    dt = neuronParameters.sim.dt
    offsetBin = int(tOffset / dt + 0.5)

    nRun = 0
    while nRun < nSweeps:
        synParametersEvoked = paramEvokedUp

        startTime = time.time()
        evokedNW = scp.NetworkMapper(cell, synParametersEvoked,
                                     neuronParameters.sim)
        evokedNW.create_saved_network2()
        stopTime = time.time()
        setupdt = stopTime - startTime
        print('Network setup time: {:.2f} s'.format(setupdt))

        synTypes = list(cell.synapses.keys())
        synTypes.sort()

        print('Testing ongoing response properties run {:d} of {:d}'.format(
            (nRun + 1, nSweeps)))
        tVec = h.Vector()
        tVec.record(h._ref_t)
        startTime = time.time()
        scp.init_neuron_run(neuronParameters.sim)
        stopTime = time.time()
        simdt = stopTime - startTime
        print('NEURON runtime: {:.2f} s'.format(simdt))

        vmSoma = np.array(cell.soma.recVList[0])
        t = np.array(tVec)
        vTraces.append(np.array(vmSoma[offsetBin:])), tTraces.append(
            np.array(t[offsetBin:]))
        #        vTraces.append(np.array(vmSoma[:])), tTraces.append(np.array(t[:]))
        for RSManager in recSiteManagers:
            RSManager.update_recordings()

        print('writing simulation results')
        fname = 'simulation'
        fname += '_run%04d' % nRun
        synName = dirName + '/' + fname + '_synapses.csv'
        print('computing active synapse properties')
        sca.compute_synapse_distances_times(synName, cell, t, synTypes)

        nRun += 1

        cell.re_init_cell()
        #        cell.remove_synapses('all')
        #        ongoingNW.re_init_network()
        evokedNW.re_init_network()

        print('-------------------------------')

    vTraces = np.array(vTraces)
    dendTraces = []
    scp.write_all_traces(dirName + '/' + uniqueID + '_vm_all_traces.csv',
                         t[offsetBin:], vTraces)
    for RSManager in recSiteManagers:
        for recSite in RSManager.recordingSites:
            tmpTraces = []
            for vTrace in recSite.vRecordings:
                tmpTraces.append(vTrace[offsetBin:])
            recSiteName = dirName + '/' + uniqueID + '_' + recSite.label + '_vm_dend_traces.csv'
            scp.write_all_traces(recSiteName, t[offsetBin:], tmpTraces)
            dendTraces.append(tmpTraces)
    dendTraces = np.array(dendTraces)

    print('writing simulation parameter files')
    neuronParameters.save(dirName + '/' + uniqueID + '_neuron_model.param')
    evokedUpNWParameters.save(dirName + '/' + uniqueID + '_network_model.param')

    spikeTimes = []
    ax = []
    fig = plt.figure()
    nrOfPlots = len(dendTraces) + 2
    for i in range(nSweeps):
        fig.add_subplot(nrOfPlots, 1, 1)
        ax.append(plt.plot(tTraces[i], vTraces[i]))
        for j in range(len(dendTraces)):
            fig.add_subplot(nrOfPlots, 1, j + 2)
            ax.append(plt.plot(tTraces[i], dendTraces[j][i]))
        fig.add_subplot(nrOfPlots, 1, nrOfPlots)
        spikeTimes.append(sca.simple_spike_detection(tTraces[i], vTraces[i]))
        print('time steps: {:d}'.format(len(tTraces[i])))
        #        print 'spike times: '
        #        print spikeTimes
        spikes = [i for t in spikeTimes[-1]]
        ax.append(plt.plot(spikeTimes[-1], spikes, 'k|'))
    fig.add_subplot(nrOfPlots, 1, 1)
    plt.xlabel('t [ms]')
    plt.ylabel('Vm [mV]')
    plt.xlim([tOffset, tStop])
    for j in range(len(dendTraces)):
        fig.add_subplot(nrOfPlots, 1, j + 2)
        plt.xlabel('t [ms]')
        labelStr = 'Vm dend site %03d [mV]' % j
        plt.ylabel(labelStr)
        plt.xlim([tOffset, tStop])
    fig.add_subplot(nrOfPlots, 1, nrOfPlots)
    plt.xlabel('t [ms]')
    plt.xlim([tOffset, tStop])

    plt.savefig(dirName + '/' + uniqueID + '_all_traces.pdf')

    hist, bins = sca.PSTH_from_spike_times(spikeTimes, 5.0, tOffset, tStop)
    scp.write_PSTH(dirName + '/' + uniqueID + '_PSTH_5ms.csv', hist, bins)


#    print 'PSTH:'
#    for i in range(len(hist)):
#        print '%.0f  %.0f  %.2f' % (bins[i], bins[i+1], hist[i])

#    plt.show()

#    plt.figure()
#    plt.plot(tTraces[0], vStd, 'k')
#    plt.xlabel('t [ms]')
#    plt.ylabel('Vm STD [mV]')
#    plt.savefig(dirName+'/'+uniqueID+'_vm_std.pdf')
#    plt.figure(3)
#    plt.hist(hist, bins=bins)
#    plt.xlabel('Vm [mV]')
#    plt.ylabel('frequency [a.u.]')
#    plt.savefig(dirName+'/'+uniqueID+'_vm_hist.pdf')

#def write_sim_results(fname, t, v):
#    with open(fname, 'w') as outputFile:
#        header = '# t\tvsoma'
#        header += '\n\n'
#        outputFile.write(header)
#        for i in range(len(t)):
#            line = str(t[i])
#            line += '\t'
#            line += str(v[i])
#            line += '\n'
#            outputFile.write(line)
#
#def write_all_traces(fname, t, vTraces):
#    with open(fname, 'w') as outputFile:
#        header = 't'
#        for i in range(len(vTraces)):
#            header += '\tVm run %02d' % i
#        header += '\n'
#        outputFile.write(header)
#        for i in range(len(t)):
#            line = str(t[i])
#            for j in range(len(vTraces)):
#                line += '\t'
#                line += str(vTraces[j][i])
#            line += '\n'
#            outputFile.write(line)


def scan_directory(path, fnames, suffix):
    for fname in glob.glob(os.path.join(path, '*')):
        if os.path.isdir(fname):
            scan_directory(fname, fnames, suffix)
        elif fname.endswith(suffix):
            fnames.append(fname)
        else:
            continue

if __name__ == '__main__':
    if len(sys.argv) == 4:
        name = sys.argv[1]
        cellName = sys.argv[2]
        networkName = sys.argv[3]
        ongoing_activity(name, cellName, networkName)
    else:
        print('Error! Number of arguments is {:d}; should be 3'.format(
            (len(sys.argv) - 1)))

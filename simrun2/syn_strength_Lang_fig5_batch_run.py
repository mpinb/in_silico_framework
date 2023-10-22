'''
create plots corresponding to Lang et al. Fig. 5
'''

import sys
import warnings
import os.path
import glob
import numpy as np
import matplotlib.pyplot as plt


def create_summary(dirName,
                   cellTypeName,
                   detectionThreshold=0.1,
                   makeplots=False):
    fnames = []
    cellTypeNames = [cellTypeName]
    scan_directory(dirName, fnames, cellTypeNames)
    print('Analyzing {:d} files!'.format(len(fnames)))
    print('cell type names', str(cellTypeNames))
    #    for f in  fnames:
    #        print f
    allData = {}
    for fname in fnames:
        splitName = fname.split('_')
        gAMPA = splitName[-8]
        gNMDA = splitName[-5]
        if gAMPA not in list(allData.keys()):
            allData[gAMPA] = {}
        if gNMDA in allData[gAMPA]:
            if makeplots:
                create_plots(fname)
            fileData = load_data(fname)
            allData[gAMPA][gNMDA]['Vm'].extend(fileData[0])
            allData[gAMPA][gNMDA]['T'].extend(fileData[1])
        else:
            allData[gAMPA][gNMDA] = {}
            if makeplots:
                create_plots(fname)
            fileData = load_data(fname)
            allData[gAMPA][gNMDA]['Vm'] = list(fileData[0][:])
            allData[gAMPA][gNMDA]['T'] = list(fileData[1][:])

    tPSPStart = 100.0

    # There has been a controvery what detection threasholds for the aPSP should be used. Roberts thesis, page 65f. mentions 0.1mV for intracortical cells and 0.15mV for thalamocortocal projections.
    #
    # However, in the code I found it to be the other way round.
    #
    # As robert suggested, I've then been looking up the threashold in the papers, Robert is refering to in his thesis.
    # This is, for the intracortical threashold Schnepel & Boucsein, Cerebral Cortex, 2015. However, in that paper, I find a threashold of 0.15 mV.
    # Roberts thesis mentions a threashold of 0.15 mV for thalamocortical connections and refers to the Constantiople & Bruno, Science, 2013
    # However, here the smallest reported aPSP is ~ 0.2mV. I mailed him and he pointed me to Bruno & Sakmann, Science, 2006, because here
    # the similar method has been used, however with thalamocortical connections from VPM to L4. Here, as Robert said, I find a value
    # of 0.165mV as lowest aPSP amplitude which matches the 0.15mV robert mentioned in his thesis.
    #
    # I therefore conclude that I can use a uniform threashold of 0.15mV
    #
    # Marcel suggests to use a threashold of 0.1 to have more data in the analysis.
    # I also make a sensitivity analysis

    #################################
    # roberts code with the old threasholds
    #################################

    #    detectionThreshold = 0.1 # VPM
    #    detectionThreshold = 0.15 # intracortical

    ##########################
    # use uniform threashold now
    ##############################

    #if  not cellTypeName in ['L2', 'L34', 'L4', 'L5st', 'L5tt', 'L6cc', 'L6ct', 'VPM']:
    #    print cellTypeName
    #    raise NotImplementedError()

    print('detectionThreshold: ', detectionThreshold)

    summaryData = {}
    for gAMPAStr in list(allData.keys()):
        summaryData[gAMPAStr] = {}
        for gNMDAStr in list(allData[gAMPAStr].keys()):
            Vm = allData[gAMPAStr][gNMDAStr]['Vm']
            tPSP = allData[gAMPAStr][gNMDAStr]['T']
            VmDetected = []
            tPSPDetected = []
            for i in range(len(Vm)):
                if Vm[i] > detectionThreshold:
                    VmDetected.append(Vm[i])
                    tPSPDetected.append(tPSP[i])
                else:
                    pass
                    #print 'ignoring aPSP of {}, because it is smaller than the threashold of {}'.format(Vm[i], detectionThreshold)
            epspMean = np.mean(VmDetected)
            epspStd = np.std(VmDetected)
            epspMed = np.median(VmDetected)
            epspMin = np.min(VmDetected)
            epspMax = np.max(VmDetected)
            tMean = np.mean(np.array(tPSPDetected) - tPSPStart)
            tStd = np.std(np.array(tPSPDetected) - tPSPStart)
            tMed = np.median(np.array(tPSPDetected) - tPSPStart)
            summaryData[gAMPAStr][
                gNMDAStr] = epspMean, epspStd, epspMed, epspMin, epspMax, tMean, tStd, tMed

    gAMPAStr = list(summaryData.keys())
    gAMPAStr.sort()
    #gNMDAStr = summaryData[gAMPAStr[0]].keys()
    #gNMDAStr.sort()
    outName = dirName
    if not dirName.endswith('/'):
        outName += '/'
    for cellTypeName in cellTypeNames:
        outName += cellTypeName + '_'
    outName += 'summary.csv'
    with open(outName, 'w') as outFile:
        header = '# gAMPA\tgNMDA\tepspMean\tepspStd\tepspMed\tepspMin\tepspMax\ttMean\ttStd\ttMed\n'
        outFile.write(header)
        for i in range(len(gAMPAStr)):
            gAMPA = gAMPAStr[i]
            gNMDA = list(summaryData[gAMPA].keys())[0]
            line = gAMPA
            line += '\t'
            line += gNMDA
            for i in range(8):
                line += '\t'
                line += str(summaryData[gAMPA][gNMDA][i])
            line += '\n'
            outFile.write(line)


#    for fname in fnames:
#        splitName = fname.split('_')
#        gEx = splitName[2]
#        summaryData[gEx] = create_plots(fname)
#
#    gExStr = summaryData.keys()
#    gExStr.sort()
#    outName = dirName
#    if not dirName.endswith('/'):
#        outName += '/'
#    outName += 'summary.csv'
#    with open(outName, 'w') as outFile:
#        header = '# gAMPA\tgNMDA\tepspMean\tepspStd\tepspMed\tepspMin\tepspMax\ttMean\ttStd\ttMed\n'
#        outFile.write(header)
#        for gEx in gExStr:
#            line = gEx
#            line += '\t'
#            line += gEx
#            for i in range(8):
#                line += '\t'
#                line += str(summaryData[gEx][i])
#            line += '\n'
#            outFile.write(line)


def scan_directory(path, fnames, cellTypeNames):
    for fname in glob.glob(os.path.join(path, '*')):
        if os.path.isdir(fname):
            scan_directory(fname, fnames, cellTypeNames)
        elif fname.endswith('vmax.csv'):
            for cellTypeName in cellTypeNames:
                #if cellTypeName in [ff for f in fname.split('/') for ff in f.split('_')] and fname not in fnames:
                if cellTypeName in fname and fname not in fnames:
                    fnames.append(fname)
        else:
            continue


def load_data(fname):
    try:
        synID, somaV, somaT = np.loadtxt(fname, skiprows=1, unpack=True)
    except ValueError:
        print('file {} is empty! Skipping. Please double-check!'.format(fname))
        return [], []
    try:  ## why?
        return list(somaV), list(somaT)
    except TypeError:
        return [somaV], [somaT]


def create_plots(fname):
    somaV, somaT = load_data(fname)
    somaV = np.array(somaV)
    somaT = np.array(somaT)

    outName = fname[:-4]
    epspName = outName + '_epsp_hist.pdf'
    dtName = outName + '_dt_hist.pdf'

    epspMean = np.mean(somaV)
    epspStd = np.std(somaV)
    epspMed = np.median(somaV)
    plt.figure()
    plt.hist(somaV, bins=np.arange(0, 1, .05))
    plt.xlabel('uEPSP amplitude at soma [$mV$]')
    plt.ylabel('frequency')
    titleStr = os.path.basename(
        fname) + ' mean uEPSP = %.2f$\pm$%.2f $mV$; median = %.2f' % (
            epspMean, epspStd, epspMed)
    plt.title(titleStr)
    plt.savefig(epspName, bbox_inches=0)

    #tMean = np.mean(somaT-10.0)
    #tStd = np.std(somaT-10.0)
    #tMed = np.median(somaT-10.0)
    #plt.figure()
    #plt.hist(somaT-10.0,bins=12)
    #plt.xlabel('time to uEPSP peak at soma [$ms$]')
    #plt.ylabel('frequency')
    #titleStr2 = fname + 'mean dt = %.2f$\pm$%.2f $mV$; median = %.2f' % (tMean,tStd,tMed)
    #plt.title(titleStr2)
    #plt.savefig(dtName, bbox_inches=0)


if __name__ == '__main__':
    dirName = sys.argv[1]
    #    create_plots(fname)
    cellTypeNames = sys.argv[2:]
    create_summary(dirName, cellTypeNames)

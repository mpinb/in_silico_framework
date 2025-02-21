'''
Analyze the membrane voltage.
'''

import numpy as np
from data_base.dbopen import dbopen

__author__ = 'Robert Egger'
__date__ = '2012-11-03'


def vm_mean(vVec, tVec, tStim, dtStim):
    '''Computes the mean voltage during a stimulation time window

    Args:
        vVec (list): voltage vector
        tVec (list): time vector
        tStim (float): start time of stimulation
        dtStim (float): duration of stimulation

    Returns:
        float: mean voltage during stimulation time window
    '''
    t = np.array(tVec)
    v = np.array(vVec)
    tEnd = tStim + dtStim
    iBegin, iEnd = 0, 0
    for i in range(1, len(t)):
        if t[i - 1] < tStim and t[i] >= tStim:
            iBegin = i
        if t[i - 1] < tEnd and t[i] >= tEnd:
            iEnd = i
    v_ = v[iBegin:iEnd]
    vss = np.mean(v_)
    return vss


def vm_std(vVec, tVec, tStim, dtStim):
    '''Computes the standard deviation of the voltage during a stimulation time window

    Args:
        vVec (list): voltage vector
        tVec (list): time vector
        tStim (float): start time of stimulation
        dtStim (float): duration of stimulation

    Returns:
        float: standard deviation of the voltage during stimulation time window
    '''
    t = np.array(tVec)
    v = np.array(vVec)
    tEnd = tStim + dtStim
    iBegin, iEnd = 0, 0
    for i in range(1, len(t)):
        if t[i - 1] < tStim and t[i] >= tStim:
            iBegin = i
        if t[i - 1] < tEnd and t[i] >= tEnd:
            iEnd = i
    v_ = v[iBegin:iEnd]
    vss = np.std(v_)
    return vss


def compute_mean_psp_amplitude(vTraces, tStim, dt, width=35.0, t_delay=15.0):
    """Compute the mean amplitude of all PSPs across multiple voltage traces.
    
    The post-synaptic potential (PSP) amplitude is the maximum membrane voltage deflection
    between :paramref:`tStim` + :paramref:`t_delay` and :paramref:`tStim` + :paramref:`delay` + :paramref:`width`.

    Args:
        vTraces (list): List of voltage traces.
        tStim (float): Timepoint of stimulation (in ms).
        dt (float): Time step of the voltage traces.
        width (float): Width of the PSP window. Default is 35.0 ms.
        t_delay (float): Delay of the PSP window (i.e. time between the stimulus and the PSP onset). Default is 15.0 ms.

    Returns:
        tuple: A tuple containing the delay and the mean amplitude of the PSPs.    
    """
    amplitudes = []
    for trace in vTraces:
        # +0.5 is simply for rounding up
        begin = int((tStim + t_delay) / dt + 0.5)
        end = int((tStim + t_delay + width) / dt + 0.5)
        amplitudes.append(np.max(trace[begin:end]))
    return [t_delay], [np.mean(amplitudes)]


def compute_vm_std_windows(vStd, tStim, dt, width=35.0, window_start_times=None):
    """Compute the standard deviation of the voltage during different time windows.
        
    Args:
        vStd (list): List of standard deviations of the voltage
        tStim (float): Time of stimulation
        dt (float): Time step.
        width (float): Width of each time window. Default is 35.0 ms.
        window_start_times (list): List of start times for the time windows. Default is [-50.0, 15.0].
        
    Returns:
        tuple: A tuple containing the time windows and the average standard deviations.
    """
    if window_start_times is None:
        window_start_times = [-50.0, 15.0]
    avgStds = []
    for t in window_start_times:
        begin = int((tStim + t) / dt + 0.5)
        end = int((tStim + t + width) / dt + 0.5)
        avgStds.append(np.mean(vStd[begin:end]))
    return np.array(window_start_times), np.array(avgStds)


def compute_vm_histogram(vTraces, bins=None):
    """Compute the histogram of membrane voltage traces.
    
    Args:
        vTraces (numpy.ndarray): Array of (one or more) voltage traces. Shape: (``n_traces``, ``n_timepoints``).
        bins (numpy.ndarray): Bins for the histogram. Default is ``np.arange(-80, -40, 2)``.

    Returns:
        tuple: The histogram and the bins
    """
    if bins is None:
        bins = np.array([-80.0 + i * 2.0 for i in range(21)])
    vPoints = vTraces.flatten()
    hist, bin_edges = np.histogram(vPoints, bins=bins)
    norm = np.max(hist)
    hist = 1.0 / norm * hist
    return hist, bins


def compute_uPSP_amplitude(t, v, tSyn, isEPSP=True, t_width_baseline=10.0):
    '''Compute the amplitude of a uPSP.
    
    Simple method for determining amplitude of a unitary post-synaptic potential (uPSP) 
    
    Args:
        t (list): Time vector
        v (list): Membrane potential vector
        tSyn (float): Timepoint of synaptic activation.
        isEPSP (bool): 
            If True, the uPSP is an excitatory post-synaptic potential (EPSP).
            If False, the uPSP is an inhibitory post-synaptic potential (IPSP). 
            Default is True.
        t_width_baseline (float): 
            Width of the time window to calculate the baseline membrane voltage. 
            Default is 10.0 ms.
    
    Returns:
        float: Amplitude of the uPSP.
    '''
    if len(t) != len(v):
        errstr = 'Time vector and membrane potential vector do not match'
        raise RuntimeError(errstr)
    
    # find baseline
    beginBin = 0
    endBin = 0
    while t[endBin] < tSyn:
        endBin += 1
    while t[beginBin] < tSyn - t_width_baseline:
        beginBin += 1
    endBin -= 1
    beginBin -= 1
    if beginBin < 0:
        beginBin = 0
    baseline = np.median(v[beginBin:endBin])

    # find amplitude wrt baseline
    if isEPSP:
        return np.max(v[endBin:]) - baseline
    else:
        return np.min(v[endBin:]) - baseline


def simple_spike_detection(
        t,
        v,
        tBegin=None,
        tEnd=None,
        threshold=0.0,
        mode='regular'):
    '''Detect spike times in a voltage trace.

    Simple spike detection method. Identifies spike times within optional window ``[tBegin, tEnd]``
    by determining :paramref:`threshold` crossing times from below.

    Args:
        t (array): Time vector
        v (array): Membrane potential vector.
        tBegin (float, optional): Start time of the detection window. Default is None (begin of voltage trace).
        tEnd (float, optional): End time of the detection window. Default is None (end of voltage trace).
        threshold (float, optional): Threshold for spike detection (mV). Default is :math:`0.0 mV`.
        mode (str, optional):
            Mode for spike detection. Default is ``regular``.
            - ``regular``: Checks if the membrane potential crosses an absolute :paramref:`threshold`.
            - ``slope``: Checks if :math:`dV/dt` is larger than a :paramref:`threshold`.

    Returns:
        list: List of spike times.
    '''
    if len(t) != len(v):
        errstr = 'Dimensions of time vector and membrane potential vector not matching'
        raise RuntimeError(errstr)

    tSpike = []
    beginIndex = 1
    endIndex = len(t)
    if tBegin is not None:
        for i in range(1, len(t)):
            if t[i - 1] < tBegin and t[i] >= tBegin:
                beginIndex = i
                break
    if tEnd is not None:
        for i in range(1, len(t)):
            if t[i - 1] < tEnd and t[i] >= tEnd:
                endIndex = i
                break

    if mode == 'regular':
        for i in range(beginIndex, endIndex):
            if v[i - 1] < threshold and v[i] >= threshold:
                tSpike.append(t[i])

    elif mode == 'slope':
        dvdt = np.diff(v) / np.diff(t)
        for i in range(beginIndex, endIndex):
            if dvdt[i - 1] < threshold and dvdt[i] >= threshold:
                tSpike.append(t[i])

    else:
        errstr = 'Unknown mode for spike detection: %s' % mode
        errstr += '\nSupported modes: regular, slope'
        raise NotImplementedError(errstr)

    return tSpike


def PSTH_from_spike_times(
        spikeTimeVectors,
        binSize=1.0,
        tBegin=None,
        tEnd=None,
        aligned=True):
    '''Calculates a PSTH from spike times.

    Args:
        spikeTimeVectors (list): List of spike time vectors.
        binSize (float, optional): Bin size for the PSTH. Default is 1.0 ms.
        tBegin (float, optional): Start time of the PSTH. Default is None (min of :paramref:`spikeTimeVectors`).
        tEnd (float, optional): End time of the PSTH. Default is None (max of :paramref:`spikeTimeVectors`).
        aligned (bool, optional): If True, aligns the bins to integer multiples of the bin size. Default is True.

    Returns:
        tuple: Tuple containing the histogram and the bins.
    '''
    norm = len(spikeTimeVectors)
    allSpikeTimes = []
    for spikeTimeVec in spikeTimeVectors:
        for spikeTime in spikeTimeVec:
            allSpikeTimes.append(spikeTime)

    if tBegin is None:
        tBegin = np.min(allSpikeTimes)
    if tEnd is None:
        tEnd = np.max(allSpikeTimes)
    if aligned:
        if tBegin >= 0:
            tBegin = int(tBegin / binSize) * binSize
        else:
            tBegin = int(tBegin / binSize - 1.0) * binSize
        tEnd = (int(tEnd / binSize) + 1.0) * binSize


    # print 'binSize = %.2f' % binSize
    # print 'tBegin = %.2f' % tBegin
    # print 'tEnd = %.2f' % tEnd

    bins = np.arange(tBegin, tEnd, binSize)
    hist, bins = np.histogram(allSpikeTimes, bins)
    if norm:
        hist = 1.0 / norm * hist

    return hist, bins


class RecordingSiteManager(object):
    '''Parse AMIRA recording sites from a ``.landmarkAscii`` file.

    Args:
        landmarkFilename (str): Path to the landmark file.
        cell (:py:class:`single_cell_parser.cell.Cell`): Cell object associated with the landmarks.

    Attributes:
        recordingSites (list): List of recording sites.
        cell (:py:class:`single_cell_parser.cell.Cell`): Cell object.
    '''
    recordingSites = None
    cell = None

    def __init__(self, landmarkFilename, cell):
        landmarks = self._read_landmark_file(landmarkFilename)
        self.cell = cell
        self.recordingSites = []
        for i in range(len(landmarks)):
            landmark = np.array(landmarks[i])
            newRecSite = self.set_up_recording_site(
                landmark, 
                i,
                landmarkFilename)
            self.recordingSites.append(newRecSite)

    def set_up_recording_site(self, location, ID, filename):
        '''Set up a :py:class:`RecordingSite` from a location.
        
        Determines the section and segment on the cell corresponding
        to the recording site location and creates new :py:class:`RecordingSite`.

        Used during initialization.

        Args:
            location (numpy.ndarray): Location of the recording site.
            ID (int): ID of the recording site.
            filename (str): Path to the AMIRA landmark file containing all recording sites.
        '''
        # inaccurate version
        #        minDist = 1e9
        #        minSecID = None
        #        minSegID = None
        #        for i in range(len(self.cell.sections)):
        #            sec = self.cell.sections[i]
        #            for j in range(len(sec.segPts)):
        #                pt = sec.segPts[j]
        #                dist = np.sqrt(np.dot(pt-location, pt-location))
        #                if(dist < minDist):
        #                    minDist = dist
        #                    minSecID = i
        #                    minSegID = j
        #
        #        sec = self.cell.sections[minSecID]
        #        somaDist = self.cell.distance_to_soma(sec, sec.relPts[minSegID])
        #        splitName = filename.split('/')[-1]
        #        tmpIndex = splitName.find('.landmarkAscii')
        #        label = splitName[:tmpIndex] + '_ID_%03d_sec_%03d_seg_%03d_somaDist_%.1f' % (ID, minSecID, minSegID, somaDist)
        #        newRecSite = RecordingSite(minSecID, minSegID, label)
        #        return newRecSite

        # precise version
        minDist = 1e9
        minSecID = None
        minSegID = None
        minx = None
        minSegx = None
        
        # Find point closest to the recording location
        for i in range(len(self.cell.sections)):
            sec = self.cell.sections[i]
            for j in range(len(sec.pts)):
                pt = sec.pts[j]
                ptx = sec.relPts[j]
                dist = np.sqrt(np.dot(pt - location, pt - location))
                if (dist < minDist):
                    minDist = dist
                    minSecID = i
                    minx = ptx
        # Find segment closest to the point
        mindx = 1.0e9
        for i in range(len(self.cell.sections[minSecID].segx)):
            x = self.cell.sections[minSecID].segx[i]
            dx = abs(x - minx)
            if dx < mindx:
                mindx = dx
                minSegx = x
                minSegID = i

        sec = self.cell.sections[minSecID]
        somaDist = self.cell.distance_to_soma(sec, minSegx)
        splitName = filename.split('/')[-1]
        tmpIndex = splitName.find('.landmarkAscii')
        # Create descriptive label
        label = \
            splitName[:tmpIndex] + \
            '_ID_%03d_sec_%03d_seg_%03d_x_%.3f_somaDist_%.1f' % (ID, minSecID, minSegID, minSegx, somaDist)
        # Set up recsite
        newRecSite = RecordingSite(minSecID, minSegID, label)
        return newRecSite

    def update_recordings(self):
        '''Add the :py:class:`~single_cell_parser.cell.Cell`'s recorded voltages to the :paramref:`recordingSites`.
        '''
        for recordingSite in self.recordingSites:
            secID = recordingSite.secID
            segID = recordingSite.segID
            vTrace = np.array(self.cell.sections[secID].recVList[segID])
            recordingSite.vRecordings.append(vTrace)

    def _read_landmark_file(self, landmarkFilename):
        '''Read the AMIRA landmark file and return the landmarks.

        Args:
            landmarkFilename (str): Path to the AMIRA landmark file.

        Returns:
            list: List of landmarks coordinates, where each element is of format (x,y,z).
        '''
        if not landmarkFilename.endswith('.landmarkAscii'):
            errstr = 'Wrong input format: has to be landmarkAscii format. Path: {p}'.format(
                p=landmarkFilename)
            raise RuntimeError(errstr)

        landmarks = []
        with dbopen(landmarkFilename, 'r') as landmarkFile:
            readPoints = False
            for line in landmarkFile:
                stripLine = line.strip()
                if not stripLine:
                    continue
                if stripLine[:2] == '@1':
                    readPoints = True
                    continue
                if readPoints:
                    splitLine = stripLine.split()
                    x = float(splitLine[0])
                    y = float(splitLine[1])
                    z = float(splitLine[2])
                    landmarks.append((x, y, z))

        return landmarks


class RecordingSite(object):
    '''Dataclass for a recording site.

    See also:
        The :py:class:`~single_cell_parser.analyze.membrane_potential_analysis.RecordingSiteManager`
        class for setting up recording sites and parsing their voltage traces.
    
    Attributes:
        secID (int): Section ID of the recording site.
        segID (int): Segment ID of the recording site.
        label (str): Identifier label.
        vRecordings (list): List of recorded voltage vectors.
            Parsed from the :py:class:`~single_cell_parser.cell.Cell`.
    '''
    secID = None
    segID = None
    label = None
    vRecordings = None

    def __init__(self, secID, segID, label):
        """    
        Args:
            secID (int): Section ID of the recording site.
            segID (int): Segment ID of the recording site.
            label (str): Identifier label.
        """
        self.secID = secID
        self.segID = segID
        self.label = label
        self.vRecordings = []


class SpikeInit:
    '''Analyze spike initiation.

    Can be used to obtain features of spike shape, adaptation etc...

    See also:
        :py:class:`biophysics_fitting.evaluator.Evaluator` for a more exhaustive analysis of voltage traces.
    '''

    def __init__(self):
        #        TODO: implement
        pass

    @staticmethod
    def vm_steady_state(cell, tVec, tStim, dtStim):
        '''Computes the "steady-state" voltage 
        
        The steady-state voltage is the median voltage during a stimulation time window.
        This can be used to define a voltage spike threshold at current intensities just below AP initiation.

        Args:
            cell (:py:class:`~single_cell_parser.cell.Cell`): Cell object.
            tVec (list): Time vector.
            tStim (float): Start time of stimulation.
            dtStim (float): Duration of stimulation.

        Returns:
            float: Steady-state voltage during :math:`[tStim, tStim+dtStim]`.
        '''
        t = np.array(tVec)
        v = np.array(cell.soma.recVList[0])
        tEnd = tStim + dtStim
        iBegin, iEnd = 0, 0
        for i in range(1, len(t)):
            if t[i - 1] < tStim and t[i] >= tStim:
                iBegin = i
            if t[i - 1] < tEnd and t[i] >= tEnd:
                iEnd = i
        v_ = v[iBegin:iEnd]
        #        steady-state can only be determined for constant
        #        current injection, not for synaptic input;
        #        therefore, use median of this trace as approximation
        vss = np.median(v_)
        return vss

    @staticmethod
    def analyze_single_spike(cell, tVec, thresh):
        '''Calculate spike height, width (FWHM) and after hyperpolarization depth (AHP).

        Only does this for a single spike in the voltage trace: the one with the
        maximum deflection from the threshold.

        Args:
            cell (:py:class:`~single_cell_parser.cell.Cell`): Cell object.
            tVec (list): Time vector.
            thresh (float): Spike threshold.

        Returns:
            tuple: Tuple containing the spike height, full width half max (FWHM), and after hyperpolarization (AHP).
        '''
        t = np.array(tVec)
        v = np.array(cell.soma.recVList[0])
        vMax = np.max(v)
        height = vMax - thresh
        halfMax = vMax - 0.5 * height
        tBegin, tEnd = 0.0, 0.0
        iEnd = 0
        for i in range(1, len(t)):
            if v[i - 1] < halfMax and v[i] >= halfMax:
                tBegin = t[i]
            if v[i - 1] >= halfMax and v[i] < halfMax:
                tEnd = t[i]
                iEnd = i
        width = tEnd - tBegin
        vMin = np.min(v[iEnd:])
        ahp = thresh - vMin
        return height, width, ahp

    @staticmethod
    def analyze_spike_train():
        """Analyze a spike train.
        
        :skip-doc:
        """
        pass

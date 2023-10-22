import neo, json, tempfile, shutil, os
from PyPDF2 import PdfFileWriter, PdfFileReader
import json
from functools import partial
import neo
import pandas as pd
import numpy as np
from model_data_base import utils as mdb_utils
from collections import defaultdict
import tempfile
import matplotlib.pyplot as plt
from IPython import display
import seaborn as sns
from model_data_base.analyze.spike_detection import spike_in_interval as mdb_analyze_spike_in_interval
from model_data_base.analyze.temporal_binning import universal as temporal_binning
from visualize import histogram

################################
# reader
################################

def read_smr_file(path):
    """Reads a Spike2 file and returns its content as a neo.core.block.Block object.

    To avoid modifying the original Spike2 file, a copy of the file is first created in a temporary folder.
    The copy is then read and returned as a neo.core.block.Block object. Finally, the temporary folder is deleted.

    Args:
        path (str): Absolute path to the Spike2 file.

    Returns:
        neo.core.block.Block: A neo.core.block.Block object containing the content of the Spike2 file.
    """
    # copying file to tmp_folder to avoid modifying it at all cost
    dest_folder = tempfile.mkdtemp()
    shutil.copy(path, dest_folder)
    path = os.path.join(dest_folder, os.path.basename(path))
    reader = neo.io.Spike2IO(filename=path)
    data = reader.read(lazy=False, signal_group_mode='split-all')[0]
    shutil.rmtree(dest_folder)
    return data


class ReaderSmr:
    '''
    A class for reading smr-files and accessing stimulus times and voltage traces.

    Args:
        path (str): The path to the smr-file.
        analogsignal_id (int): The ID of the analog signal to read.
        stim_times_channel (str): The name of the channel containing the stimulus times.
        min_rel_time (float): The minimum relative time to include in the voltage traces.
        max_rel_time (float): The maximum relative time to include in the voltage traces.

    Attributes:
        path (str): The path to the smr-file.
        analogsignal_id (int): The ID of the analog signal to read.
        stim_times_channel (str): The name of the channel containing the stimulus times.
        min_rel_time (float): The minimum relative time to include in the voltage traces.
        max_rel_time (float): The maximum relative time to include in the voltage traces.
        t (numpy.ndarray): The time points of the voltage traces.
        v (numpy.ndarray): The voltage values of the traces.
        stim_times (list): The times of the stimuli.
        t_start (float): The start time of the voltage traces.
        t_end (float): The end time of the voltage traces.
    '''

    def __init__(self,
                 path,
                 analogsignal_id=0,
                 stim_times_channel=None,
                 min_rel_time=None,
                 max_rel_time=None):
        self.path = path
        self.analogsignal_id = analogsignal_id
        self.stim_times_channel = stim_times_channel
        self.min_rel_time = min_rel_time
        self.max_rel_time = max_rel_time

        # voltage traces
        self._data = data = read_smr_file(path)
        asig = data.segments[0].analogsignals[analogsignal_id]
        self.t = asig.times.rescale('s').magnitude.flatten() * 1000
        self.v = asig.magnitude.flatten()

        # stim_times
        if stim_times_channel:
            self._events = events = {
                e.annotations['id']: e for e in data.segments[0].events
            }
            self.stim_times = np.array(events[stim_times_channel]) * 1000
        else:
            self.stim_times = []

        if max_rel_time:
            self.v = self.v[self.t < max(self.stim_times) + max_rel_time]
            self.t = self.t[self.t < max(self.stim_times) + max_rel_time]
        if min_rel_time:
            self.v = self.v[self.t > min(self.stim_times) - min_rel_time]
            self.t = self.t[self.t > min(self.stim_times) - min_rel_time]

        self.t_start = self.t[0]
        self.t_end = self.t[-1]

    def get_voltage_traces(self):
        '''
        Returns the time points and voltage values of the traces.

        Returns:
            tuple: A tuple containing the time points and voltage values of the traces.
        '''
        return self.t, self.v

    def get_stim_times(self):
        '''
        Returns the times of the stimuli.

        Returns:
            list: A list containing the times of the stimuli.
        '''
        return list(self.stim_times)

    def get_serialize_dict(self):
        '''
        Returns a dictionary containing the attributes of the ReaderSmr object.

        Returns:
            dict: A dictionary containing the attributes of the ReaderSmr object.
        '''
        return {
            'path': self.path,
            'analogsignal_id': self.analogsignal_id,
            'stim_times_channel': self.stim_times_channel,
            'stim_times': list(self.stim_times),
            'class': 'ReaderSmr',
            'min_rel_time': self.min_rel_time,
            'max_rel_time': self.max_rel_time
        }


class ReaderDummy:
    '''Not a reader. You provide the data.'''

    def __init__(self, t, v, stim_times=[0]):

        # voltage traces
        self.t = t
        self.v = v
        self.stim_times = stim_times
        self.t_start = 0
        self.t_end = max(t)

    def get_voltage_traces(self):
        return self.t, self.v

    def get_stim_times(self):
        return list(self.stim_times)


def read_labview_junk1_dat_files(path, scale=100, sampling_rate=32000):
    import numpy as np
    with open(path, 'rb') as f:
        while f.read(1) != '\x00':  # skip header
            pass
        data = np.fromfile(
            f, dtype='>f4')  # interpret binary data as big endian float32
    t = [lv * 1. / sampling_rate for lv in range(len(data))]
    return np.array(t) * 1000, data * scale


def highpass_filter(y, sr):
    '''https://dsp.stackexchange.com/questions/41184/high-pass-filter-in-python-scipy'''
    from scipy import signal
    filter_stop_freq = 70  # Hz
    filter_pass_freq = 100  # Hz
    filter_order = 1001

    # High-pass filter
    nyquist_rate = sr / 2.
    desired = (0, 0, 1, 1)
    bands = (0, filter_stop_freq, filter_pass_freq, nyquist_rate)
    filter_coefs = signal.firls(filter_order, bands, desired, nyq=nyquist_rate)

    # Apply high-pass filter
    filtered_audio = signal.filtfilt(filter_coefs, [1], y)
    return filtered_audio


class ReaderLabView:

    def __init__(self,
                 path,
                 stim_times=None,
                 sampling_rate=32000,
                 scale=100,
                 apply_filter=False):
        self.path = path
        self.stim_times = stim_times
        self.sampling_rate = sampling_rate
        self.scale = scale
        self.apply_filter = apply_filter
        self.t, self.v = read_labview_junk1_dat_files(
            path, scale=scale, sampling_rate=sampling_rate)
        if apply_filter:
            self.v = highpass_filter(self.v, sampling_rate)
        if stim_times is None:
            stim_times = []
        self.t_start = self.t[0]
        self.t_end = self.t[-1]

    def get_stim_times(self):
        return list(self.stim_times)

    def get_voltage_traces(self):
        return self.t, self.v

    def get_serialize_dict(self):
        return {
            'path': self.path,
            'stim_times': self.stim_times,
            'sampling_rate': self.sampling_rate,
            'scale': self.scale,
            'class': 'ReaderLabView',
            'apply_filter': self.apply_filter
        }


def load_reader(dict_):
    class_ = dict_.pop('class')
    if class_ == 'ReaderSmr':
        path = dict_.pop('path')
        try:
            dict_.pop('stim_times')
        except KeyError:
            pass
        return ReaderSmr(path, **dict_)
    else:
        raise NotImplementedError()


######################################
# methods for extracting spike times from voltage trace
# methods for filtering spike times based on waveform features (creast and trough)
######################################


def get_peaks_above(t, v, lim):
    """
    Compute timepoints of maxima above a threshold.

    Args:
        t (list): A list containing timepoints.
        v (list): A list containing recorded voltage.
        lim (float): A threshold above which (>=) maxima are detected.

    Returns:
        max_t (list): A list containing timepoints of maxima.
        max_v (list): A list containing voltage at timepoints of maxima.
    """
    assert len(t) == len(v)
    v, t = np.array(v), np.array(t)
    left_diff = v[1:-1] - v[:-2]
    right_diff = v[1:-1] - v[2:]
    values = v[1:-1]
    # use >= because sometimes the spikes reach the threshold of the amplifier of +5mV
    # by >, they would not be detected
    indices = np.argwhere((left_diff >= 0) & (right_diff >= 0) &
                            (values >= lim)).ravel() + 1
    return list(t[indices]), list(v[indices])


def get_upcross(t, v, lim):
    """
    Finds the times and corresponding voltages of upcrossings of a given threshold.

    Args:
        t (numpy.ndarray): Array of time values.
        v (numpy.ndarray): Array of voltage values.
        lim (float): Threshold value.

    Returns:
        Tuple[numpy.ndarray, numpy.ndarray]: Tuple containing arrays of time and voltage values at upcrossings.
    """
    indices = np.argwhere((v[:-1] < lim) & (v[1:] >= lim)).ravel() + 1
    return t[indices], v[indices]


def filter_spike_times(
    spike_times,
    spike_times_trough,
    creast_trough_interval=2,
    mode='latest',
    spike_times_amplitude=None,
    upper_creast_threshold=None,
    creast_upcross_times=None,
):
    ''' Filter spike times based on timepoints of detected creasts and troughs. 
    
    Idea: A spike is detected by its trough. Then, it is checked, that there is
    a corresponding creast at maximum 2ms before the trough. All creasts fullfilling
    this criterion are extracted. The spike time is set to the latest creast (if mode = 'latest')
    or the maximum creast amplitude (if mode = 'creast_max'). 
    
    If a through does not have a corresponding creast, no spike is detected.
    
    Args:
        - spike_times: list, containing spike times defined by the creast of the waveform
        - spike_times_trough, list, containing spike times defined by the trough of the waveform
    
    Returns:
        filtered_spike_times: list, containing spikes fullfilling the definition above.'''
    if not mode in ['latest', 'creast_max']:
        raise ValueError("mode must be 'latest' or 'creast_max'!")
    s = []
    s_ampl = []
    spike_times = np.array(spike_times)
    for x in spike_times_trough:
        aligned_creasts = spike_times[
            (spike_times >= x - creast_trough_interval) &
            (spike_times
             < x)]  # [y for y in spike_times if (y < x) and (y >= x-2)]
        aligned_creast_amplitude = spike_times_amplitude[
            (spike_times >= x - creast_trough_interval) & (spike_times < x)]
        # artifact detection to get rid of traces that depolarize far beyond typical AP height
        if upper_creast_threshold is not None:
            if (spike_times_amplitude[(spike_times >= x -
                                       creast_trough_interval - 5) &
                                      (spike_times < x)]
                    > upper_creast_threshold).any():
                continue
        if len(aligned_creasts) > 0:
            if mode == 'latest':
                assert aligned_creasts.max() == aligned_creasts[-1]
                s.append(aligned_creasts[-1])  # before: aligned_creats[0]
                s_ampl.append(aligned_creast_amplitude[-1])
            if mode == 'creast_max':
                index = np.argmax(aligned_creast_amplitude)
                s_ampl.append(aligned_creast_amplitude[index])
                s.append(aligned_creasts[index])
    return np.array(s), np.array(s_ampl)


def filter_short_ISIs(t, tdelta=0.):
    """
    Filters out any events that occur in an interval shorter than tdelta.

    Args:
        t (list): A list containing timepoints of events.
        tdelta (float, optional): Minimal interval between events. Defaults to 0.

    Returns:
        list: A list containing filtered spike times.

    Examples:
        >>> filter_short_ISIs([1,2,3,4,5], tdelta=1.5)
        [1, 3, 5]

        >>> filter_short_ISIs([1,2,3,4,5], tdelta=2)
        [1, 3, 5]
    """
    if len(t) == 0:
        return []

    out_t = [t[0]]

    for tt in t[1:]:
        if tt - out_t[-1] >= tdelta:
            out_t.append(tt)

    return out_t


###########################################
# methods for interpreting stimulus times
###########################################


def _find_stimulus_interval(stim_times):
    '''helper function to get the interval between the stimuli.
    Assumption: The stimulus interval is constant.'''
    return stim_times[1] - stim_times[0]


def stimulus_interval_filter(stim_times, period_length=1, offset=0):
    """
    Filters periodic stimuli such that only the first stimulus of each period is retained.

    Args:
        stim_times (list): A list containing stimulus times.
        period_length (int, optional): The number of stimuli forming one period. Defaults to 1.
        offset (int, optional): The number of the stimulus in each period to be extracted. Defaults to 0.

    Returns:
        list: A list containing filtered stimulus times.

    Examples:
        >>> stimulus_interval_filter([1,2,3,4])
        [1, 2, 3, 4]

        >>> stimulus_interval_filter([1,2,3,4], period_length=2)
        [1, 3]

        >>> stimulus_interval_filter([1,2,3,4], period_length=2, offset=1)
        [2, 4]
    """
    return stim_times[offset::period_length]


## automatic interval detection ... not to be trusted
#     max_interval = max(set(np.diff(stim_times).round()))
#     out = []
#     for i in intervals:
#         if out:
#             if i - out[-1] < max_interval - 5:
#                 continue
#         out.append(i)
#     return out


#####################################################
# convert list of spike times and list of stim times into dataframe
#####################################################

def get_st_from_spike_times_and_stim_times(spike_times,
                                           stim_times,
                                           offset = 0,
                                           mode = 'spike_times'):
    """Computes spike times dataframe based on list of spike times and stimulus times.

    Args:
        spike_times (list[float]): List of spike times.
        stim_times (list[float]): List of stimulus times.
        offset (float, optional): Offset value. Defaults to 0.
        mode (str, optional): Mode of computation. Can be 'spike_times' or 'ISIs'. Defaults to 'spike_times'.

    Returns:
        pd.DataFrame: Pandas dataframe. Its format is as follows: One row is one trial. The columns contain the spike times
        and are named in ascending order (0,1,2, ...).

    Raises:
        ValueError: If mode is not 'spike_times' or 'ISIs'.
        ValueError: If offset is not negative.
    """
    if len(stim_times) == 0:
        stim_interval = np.Inf
        stim_times = [0.]
    elif len(stim_times) == 1:
        stim_interval = np.Inf
    else:
        stim_interval = _find_stimulus_interval(stim_times)
    if offset > 0:
        raise ValueError('offset has to be negative.')
    if mode == 'spike_times':
        out = []
        for lv, stim_time in enumerate(stim_times):
            values = [
                s - stim_time
                for s in spike_times
                if ((s - stim_time) >= offset) and (
                    (s - stim_time) < stim_interval + offset)
            ]
            values = pd.Series({lv: v for lv, v in enumerate(values)})
            values.name = lv
            out.append(values)
        return pd.DataFrame(out)
    elif mode == 'ISIs':
        out_ISIs = []
        ISIs = pd.Series(spike_times).diff().tolist()
        for lv, stim_time in enumerate(stim_times):
            values = [
                s[1]
                for s in zip(spike_times, ISIs)
                if ((s[0] - stim_time) >= offset) and (
                    (s[0] - stim_time) < stim_interval + offset)
            ]
            values = pd.Series({lv: v for lv, v in enumerate(values)})
            values.name = lv
            out_ISIs.append(values)
        return pd.DataFrame(out_ISIs)
    else:
        raise ValueError('mode must be spike_times or ISIs')



def strip_st(st):
    """
    Returns a DataFrame containing only spike times, without metadata.
    
    Args:
        st: A pandas DataFrame containing spike times as generated by get_st_from_spike_times_and_stim_times
    
    Returns:
        A pandas DataFrame, in which all columns that cannot be converted to integer are filtered out,
        i.e. the DataFrame contains only spike times and no metadata.
    """
    return st[[c for c in st.columns if mdb_utils.convertible_to_int(c)]]


import pandas as pd

def get_spike_times_from_row(row):
    """Returns a list containing all non-NaN elements in the given pandas Series.
    
    Args:
        row (pd.Series): A pandas Series containing spike times.
        
    Returns:
        list: A list containing spike times.
    """
    row = row.dropna()
    import six
    row = [v for i, v in six.iteritems(row)]
    return row


class SpikeDetectionCreastTrough(object):
    '''Detects spikes by creast and trough amplitude.
    
    Parameters
    ----------
    reader_object: object with get_voltage_traces and get_stim_times method, e.g. SmrReader
    lim_creast: float or str, threashold above which a creast of a spike is detected 
        as such. Needs to be float or "minimum", or "zero". If "minimum" or "zero" is choosen, 
        the threashold will be set based on the histogram of all creasts. If "minimum" is 
        choosen, lim_creast will be set to the first minimum in the histogram above or equal to 0.4mV. 
        If "zero" is choosen, lim_creast will be set to the first empty bin.
    lim_trough: float or str, as lim_creast. If float is specified, you probably 
        want to use a negative value. lim creast and lim_trough need to be both floats, both 
        "zero" or both "minimum".
    max_creast_trough_interval: float. Maximum interval between creast and trough such that 
        a spike is recognized.
    tdelta: float, minimum interval between spikes
    stimulus_period: int, number of stimuli applied per trial. E.g., for paired pulse stimuli,
        it should be 2.
    stimulus_period_offset: int, number of stimulus that initiates first trial.
    cellid: str, name to be used in spike times dataframe
    
    Attributes
    ----------
    lim_creast: lim_creast used for spike detection (if "minimum" or "zero" was defined, this will
        be the numeric value used"
    lim_trough: as above
    st: spike times dataframe, one row per trial
    spike_times: all extracted spike times, fullfilling creast and trough criterion, filtered such that
        the minimal ISI is above tdelta.
    _spike_times_creast: spike times fullfilling creast criterion
    _spike_times_trough: spike times fullfilling trough criterien'''

    def __init__(self,
                 reader_object,
                 lim_creast='minimum',
                 lim_trough='minimum',
                 max_creast_trough_interval=2.,
                 tdelta=1.,
                 stimulus_period=1,
                 stimulus_period_offset=0,
                 upper_creast_threshold=np.inf,
                 cellid='__no_cellid_assigned__',
                 spike_time_mode='latest'):
        self.reader = reader_object
        self.stimulus_period = stimulus_period
        self.stimulus_period_offset = stimulus_period_offset
        self.stim_times = stimulus_interval_filter(
            reader_object.get_stim_times(), stimulus_period,
            stimulus_period_offset)
        self.tdelta = tdelta
        self.cellid = cellid
        self.upper_creast_threshold = upper_creast_threshold
        self.max_creast_trough_interval = max_creast_trough_interval
        self._lim_creast = lim_creast
        self._lim_trough = lim_trough
        self._set_creast_trough(self._lim_creast, self._lim_trough)
        self.spike_time_mode = spike_time_mode

    def run_analysis(self):
        self._extract_spike_times()

    def _set_creast_trough(self, lim_creast, lim_trough):
        # automatic detection of creast and trough limit
        if lim_creast == 'minimum' and lim_trough == 'minimum':
            lim_creast, lim_trough = self.get_creast_and_trough_ampltidues_by_bins(
                'minimum')
        elif lim_creast == 'zero' and lim_trough == 'zero':
            lim_creast, lim_trough = self.get_creast_and_trough_ampltidues_by_bins(
                'zero')
        elif isinstance(lim_creast, float) and isinstance(lim_trough, float):
            pass
        else:
            raise ValueError(
                'lim_creast and lim_trough must be both floats or both be "minimum" or both be "zero"'
            )
        if lim_creast < 0:
            print("warning: lim_creast is < 0")
        if lim_trough > 0:
            print("warning: lim_trough is > 0")
        self.lim_creast = lim_creast
        self.lim_trough = lim_trough

    def _extract_spike_times(self):
        # aliases
        t, v = self.reader.get_voltage_traces()
        lim_creast, lim_trough = self.lim_creast, self.lim_trough
        tdelta = self.tdelta
        upper_creast_threshold = self.upper_creast_threshold
        # spike times detected by creast
        a, b = get_peaks_above(t, v, lim_creast)
        self._spike_times_creast, self._spike_amplitudes_creast = a, np.array(
            b)
        #self._spike_times_creast_filtered = filter_short_ISIs(self._spike_times_creast, tdelta=tdelta)
        # spike times detected by trough
        a, b = get_peaks_above(t, v * -1, lim_trough * -1)
        self._spike_times_trough, self._spike_amplitudes_trough = a, b
        #self._spike_times_trough_filtered = filter_short_ISIs(self._spike_times_trough, tdelta=tdelta)
        # spike times detected by creast and trough
        self.spike_times, self.spike_times_amplitude = filter_spike_times(
            self._spike_times_creast,
            self._spike_times_trough,
            creast_trough_interval=self.max_creast_trough_interval,
            spike_times_amplitude=self._spike_amplitudes_creast,
            upper_creast_threshold=upper_creast_threshold,
            mode=self.spike_time_mode)
        # remove spike times that cross max_threshold
        self.spike_times = filter_short_ISIs(self.spike_times, tdelta=tdelta)

        self.t_start = self.reader.t_start
        self.t_end = self.reader.t_end

    def get_creast_and_trough_ampltidues_by_bins(self, mode='zero'):
        # aliases
        t, v = self.reader.get_voltage_traces()
        t, v = np.array(t), np.array(v)

        if len(self.stim_times) < 2:
            str_ = "less than 2 stimuli found. using whole trace to determine "
            str_ += "lim_creast and lim_trough."
        else:
            str_ = "using interval between first stimlus and last stimulus to determine "
            str_ += "lim_creast and lim_trough."
            index = (self.stim_times[0] < t) & (t < self.stim_times[-1])
            t = t[index]
            v = v[index]
        print(str_)

        # get peak and creast amplitude
        _, creasts = get_peaks_above(t, v, 0)
        _, troughs = get_peaks_above(t, v * -1, 0)

        # compute bins
        bins = np.arange(0, 7, 0.1)
        binned_data_st, _ = np.histogram(creasts, bins=bins)
        binned_data_sst, _ = np.histogram(troughs, bins=bins)
        if mode == 'zero':
            minimun_zero_bin_st = bins[np.argwhere(
                binned_data_st[4:-1] == 0).min() + 4]
            minimun_zero_bin_sst = bins[np.argwhere(
                binned_data_sst[4:-1] == 0).min() + 4]
        elif mode == 'minimum':
            minimun_zero_bin_st = bins[np.argwhere(
                ((binned_data_st[4:-1] - binned_data_st[5:]) < 0) |
                (binned_data_st[4:-1] == 0)).min() + 4]
            minimun_zero_bin_sst = bins[np.argwhere(
                ((binned_data_sst[4:-1] - binned_data_sst[5:]) < 0) |
                (binned_data_sst[4:-1] == 0)).min() + 4]
        return minimun_zero_bin_st, minimun_zero_bin_sst * -1

    def get_default_events(self,
                           show_stim_times=True,
                           show_trough_candidates=True):
        '''Returns a list of events to be displayed with the show_events method.
        Creates events for deteced spikes (black line) and spike candidates [dotted black line]
        (i.e. creasts and troughs exceeding the limit but which do not qualify to 
        be a spike)
        
        Parameters
        ----------
        show_spike_times: 
        
        Returns
        -------
        events: list, containing 4-tuples of the format (time, color, linestyle, linewidth)'''
        # get unsuccessful spike candidates
        events = [
            (s, 'k', '--', .5)
            for s in self._spike_times_creast
            if not s in self.spike_times
        ]  # len([ss for ss in self.spike_times if np.abs(ss-s) < 1])]
        if show_trough_candidates:
            events += [(s, 'k', '--', .5)
                       for s in self._spike_times_trough
                       if not len([
                           ss for ss in self.spike_times
                           if 0 < s - ss < self.max_creast_trough_interval
                       ])]
        # get detected spikes
        events += [(t, 'pink', '-', 3) for t in self.spike_times]
        # add stimulus times
        if show_stim_times:
            events += [(t, 'r', '-', 3) for t in self.stim_times]
        return events

    def show_events(self,
                    events='auto',
                    savepdf=None,
                    showfig=True,
                    ylim=(-5, 5)):
        '''Shows voltage trace, threasholds and events.
        
        Parameters
        ----------
        events: 'auto': uses the get_default_events_method. shows detected spikes as black line, spike candidates 
                     as dotted black line, stimulus times as bold red line
                'only_creast': 
                list: explicitly define events to show. Needs to be list containing 4-touples in the following format
                     (timepoint, 'color', 'linestyle', linewidth)'''
        if events == 'auto':
            events = self.get_default_events()
        if events == 'only_creast':
            events = self.get_default_events(show_trough_candidates=False)
        elif isinstance(events, list):
            pass
        else:
            raise ValueError(
                "events must be auto, only_creast, or of type list")
        events = sorted(events, key=lambda x: x[0])
        if savepdf:
            output = PdfFileWriter()

        t, v = self.reader.get_voltage_traces()
        n = 0
        while True:
            try:
                offset_time = events[n][0]
            except IndexError:
                break
            index = (t > offset_time - 15) & (t < offset_time + 15)
            tt, vv = t[index], v[index]
            fig = plt.figure(figsize=(15, 4))
            plt.plot(tt, vv)  ###
            plt.axhline(self.lim_creast, color='grey', linewidth=.5)
            plt.axhline(self.lim_trough, color='grey', linewidth=.5)
            plt.axhline(self.upper_creast_threshold,
                          color='red',
                          linewidth=.5)

            for lv, (event_t, c, linestyle, linewidth) in enumerate(events):
                if offset_time - 15 <= event_t <= offset_time + 15:
                    plt.axvline(event_t,
                                  color=c,
                                  linewidth=linewidth,
                                  linestyle=linestyle,
                                  alpha=0.6)
                    n = lv  # n is index of last event shown
            n += 1
            plt.gca().ticklabel_format(useOffset=False)
            sns.despine()
            plt.ylim(*ylim)
            plt.xlabel('t / ms')
            plt.ylabel('recorded potential / mV')
            if showfig:
                display.display(fig)
            if savepdf:
                fig.savefig(savepdf)
                inputpdf = PdfFileReader(savepdf, "rb")
                output.addPage(inputpdf.getPage(0))
            plt.close()
        if savepdf:
            with open(savepdf, "wb") as outputStream:
                output.write(outputStream)

    def get_serialize_dict(self):
        return {
            'reader_object': self.reader.get_serialize_dict(),
            'lim_creast': self.lim_creast,
            'lim_trough': self.lim_trough,
            'max_creast_trough_interval': self.max_creast_trough_interval,
            'tdelta': self.tdelta,
            'stimulus_period': self.stimulus_period,
            'stimulus_period_offset': self.stimulus_period_offset,
            'stim_times': self.stim_times,
            'cellid': self.cellid,
            'spike_times': self.spike_times,
            '_spike_times_creast': self._spike_times_creast,
            '_spike_times_trough': self._spike_times_trough,
            't_start': self.t_start,
            't_end': self.t_end
        }

    def save(self, path):
        with open(path, 'w') as out:
            json.dump(self.get_serialize_dict(), out)

    @staticmethod
    def load(path, init_reader=False):
        ret = SpikeDetectionCreastTrough.__new__(SpikeDetectionCreastTrough)
        with open(path) as f:
            data = json.load(f)
        import six
        for k, v in six.iteritems(data):
            setattr(ret, k, v)
        if init_reader:
            ret.reader = load_reader(data['reader_object'])
        if not 'stim_times' in list(data.keys()):
            ret.stim_times = stimulus_interval_filter(
                ret.reader.get_stim_times(), ret.stimulus_period,
                ret.stimulus_period_offset)
        return ret

    def plot_creast_trough_histogram(self, ax=None):
        pass  # todo


#################################################
# classify timepoint at which a spike occurs
#################################################
def get_period_label_by_time(periods, t):
    '''Classifies timepoint.
    
    Parameters
    ----------
    periods: dict, containing period label as key and (period_start, period_end) as value
    t: float, timepoint to classify
    
    Returns
    -------
    label: label of period in which t is in. 'undefined' if t is in no defined period'''

    import six
    for k, (tmin, tmax) in six.iteritems(periods):
        if tmin <= t < tmax:
            return k
    return 'undefined'


#################################################
# methods for analyzing events (doublets, bursts)
#################################################


def _spike_times_series_from_spike_times_dataframe(st):
    '''Converts a spike times dataframe to a pd.Series, which has the following format:
    keys: same as keys in st
    values: list of spike times, as in st, but without NaN and metadata.'''
    st = strip_st(st)
    dummy = [
        (name, get_spike_times_from_row(row)) for name, row in st.iterrows()
    ]
    spike_times = pd.Series([d[1] for d in dummy],
                              index=[d[0] for d in dummy])
    return spike_times


def _sta_apply_helper(spike_times, analysis_function, periods={}):
    '''helper function for applying an analysis_function on spike_times in
    the following special case:
    
    spike_times is a pd.Series in the format of SpikeTimesAnalysis.spike_time,
    i.e. it contains lists of spike times as values and trials as keys.
    
    analysis_function is called by a list of spike_times and returns a pd.DataFrame.
    The dataframe contains at least the following columns:
        event_type: type of the event
        event_time: timepoint of event occurence
    
    The dataframe will be extended with the column "trial", which is determined based
    on the  key of the pd.Series.
    
    Parameters
    ----------
    spike_times: pd.Series, containing lists of spike_times (see above).
    analysis_function: function that gets a single list of spike times and returns pd.DataFrame
    
    Returns
    -------
    pd.DataFrame, in which the individual dataframes returned by analysis_function are 
    concatenated.
    '''
    import six
    out = []
    for name, spike_times in six.iteritems(spike_times):
        df = analysis_function(spike_times)
        df['trial'] = name
        out.append(df)
    out = pd.concat(out).reset_index(drop=True)
    out['period'] = out.apply(
        lambda x: get_period_label_by_time(periods, x.event_time), axis=1)
    return out


def _sta_input_checker(t_start, t_end, period):
    errstr = 'You can define period or t_start and t_end, but not both.'
    if period:
        if t_start or t_end:
            raise ValueError(errstr)
    if t_start or t_end:
        if not t_start and t_end:
            raise ValueError(errstr)
    return t_start, t_end, period


class STAPlugin_TEMPLATE(object):

    def __init__(self):
        self._result = None

    def get_result(self):
        if self._result is None:
            raise RuntimeError("You need to call setup first")
        else:
            return self._result

    def setup(self):
        raise NotImplementedError


class STAPlugin_ISIn(STAPlugin_TEMPLATE):

    def __init__(self, name='ISIn', source='spike_times', max_n=5):
        self.name = name
        self.source = source
        self.max_n = max_n
        STAPlugin_TEMPLATE.__init__(self)

    def setup(self, spike_times_analysis):
        times = spike_times_analysis.get(self.source)
        self._result = self.event_analysis_ISIn(times, self.max_n)

    @staticmethod
    def event_analysis_ISIn(spike_times, n=5):
        '''Computes for each spike the inter spike interval (ISI) to the next, second next, nth spike.
        
        Parameters
        ----------
        spike_times: list, containing spike times
        n: max order of ISIs computed (e.g. if n = 1, only the interval to the next spike will be computed.
        
        Returns
        -------
        out: pandas.DataFrame, containing the columns ISI_1 to ISI_{n}, and event_time
            The ISI_{} columns contain the time interval between the current spike (@ event time) 
            and the nth next spike. np.NaN, if there is no nth next spike.
        '''
        out = []
        #n = min(n, len(spike_times))
        for lv in range(len(spike_times)):
            time = spike_times[lv]
            ISIs = {}
            for nn in range(1, n):
                try:
                    spike_times[lv + nn]
                except IndexError:
                    continue
                ISIs['ISI_{}'.format(nn)] = spike_times[lv + nn] - time
            ISIs['event_time'] = time
            out.append(ISIs)
        return pd.DataFrame(out)


class STAPlugin_bursts(STAPlugin_TEMPLATE):

    def __init__(self,
                 name='bursts',
                 source='spike_times',
                 event_maxtimes={
                     0: 0,
                     1: 10,
                     2: 30
                 },
                 event_names={
                     0: 'singlet',
                     1: 'doublet',
                     2: 'triplet'
                 }):
        STAPlugin_TEMPLATE.__init__(self)
        self.name = name
        self.source = source
        self.event_maxtimes = event_maxtimes
        self.event_names = event_names

    def setup(self, spike_times_analysis):
        times = spike_times_analysis.get(self.source)
        self._result = self.event_analysis_bursts(times, self.event_maxtimes,
                                                  self.event_names)

    @staticmethod
    def event_analysis_bursts(row, event_maxtimes=None, event_names=None):
        '''Detects high frequency events (doublet, triplet, ...) that occur within a timewindow.
        
        Parameters
        ----------
        row: list-like, containing spike times
        event_maxtimes: dictionary, keys indicate event type (0 mean singlet, 1 mean doublet, 2 means triplet, ...),
            values indicate max duration of such an event.
        event_name: dictionary, names of the events (0: 'singlet', 1:'doublet', 2:'triplet')
        
        Returns
        -------
        out: pandas.DataFrame, one row is one event. Columns are:
            event_time: timepoint of first_spike belonging to event
            event_class: class of event as defined in event_name
            ISI_{n}: Interval from first spike of event to nth spike to event
            
            An event is allways classified as the one with the highest number of spikes possible,
            e.g. [1,5,9] could be classified as doublet + singlet, but it will be a triplet.
        '''
        if not sorted(event_maxtimes.keys()) == sorted(event_names.keys()):
            raise ValueError(
                'keys of event_maxtimes and event_name must be the same!')
        if not 0 in event_maxtimes:
            raise ValueError(
                '0 / singlet must be defined! Please check event_maxtimes and event_name.'
            )

        events_in_descending_order = sorted(list(event_maxtimes.keys()),
                                            reverse=True)

        row = np.array(row)
        out = []
        lv = 0
        while True:
            row_section = row[lv:]
            # terminate loop, if all spikes have been processed
            if len(row_section) == 0:
                break
            isis = row_section - row_section[0]
            # check if event is present, starting with highest event
            for n in events_in_descending_order:
                if n >= len(isis):
                    continue
                if isis[n] <= event_maxtimes[n]:
                    break
            out_dict = {'ISI_{}'.format(nn): isis[nn] for nn in range(1, n + 1)}
            out_dict['event_time'] = row_section[0]
            out_dict['event_class'] = event_names[n]

            out.append(out_dict)
            lv += 1 + n
        return pd.DataFrame(out)


class STAPlugin_annotate_bursts_in_st(STAPlugin_TEMPLATE):

    def __init__(self,
                 name='bursts_st',
                 source='st',
                 event_maxtimes={
                     0: 0,
                     1: 10,
                     2: 30
                 },
                 event_names={
                     0: 'singlet',
                     1: 'doublet',
                     2: 'triplet'
                 }):
        self.name = name
        self.source = source
        self.event_maxtimes = event_maxtimes
        self.event_names = event_names

    def setup(self, spike_times_analysis):
        st = spike_times_analysis.get(self.source)
        st = strip_st(st)

        dfs = [
            STAPlugin_bursts.event_analysis_bursts(row.dropna(),
                                                   self.event_maxtimes,
                                                   self.event_names)
            for i, row in strip_st(st).iterrows()
        ]

        import six
        event_names_inverse = {
            v: k + 1 for k, v in six.iteritems(self.event_names)
        }

        def fun(s):
            l_ = [[e] * event_names_inverse[e] for e in s]
            l_ = [x for x in l_ for x in x]
            return pd.Series(l_)

        df = pd.concat(
            [fun(df.event_class) if len(df) else pd.Series() for df in dfs],
            axis=1).T
        df.index = st.index
        self._result = df


class STAPlugin_ongoing(STAPlugin_TEMPLATE):

    def __init__(self,
                 name='ongoing_activity',
                 source='spike_times',
                 ongoing_sample_length=90000,
                 mode='frequency'):
        STAPlugin_TEMPLATE.__init__(self)
        if not mode in ('frequency', 'count'):
            raise ValueError('mode must be "frequency" or "count"!')
        self.name = name
        self.source = source
        self.ongoing_sample_length = ongoing_sample_length
        self.mode = mode

    def setup(self, spike_times_analysis):
        spike_times = spike_times_analysis.get(self.source)
        stim_times = spike_times_analysis.get('stim_times')
        first_stim = min(stim_times)
        recording_start = max(spike_times_analysis.spike_times_object.t_start,
                              0)
        epsilon = 0.1
        if first_stim - self.ongoing_sample_length + epsilon < recording_start:
            # raise RuntimeError('cannot compute ongoing activity')
            self._result = float('nan')
        n_spikes = [
            s for s in spike_times
            if first_stim - self.ongoing_sample_length <= s < first_stim
        ]
        n_spikes = float(len(n_spikes))
        if self.mode == 'frequency':
            self._result = float(n_spikes) / self.ongoing_sample_length * 1000
        elif self.mode == 'count':
            self._result = n_spikes


class STAPlugin_quantification_in_period(STAPlugin_TEMPLATE):

    def __init__(self,
                 name='frequency_in_period',
                 source='st_df',
                 period=None,
                 t_start=None,
                 t_end=None,
                 mode='frequency'):
        if not mode in ('frequency', 'count_per_trial', 'count_total'):
            raise ValueError(
                'mode must be "frequency" or "count_per_trial" or "count_total"!'
            )
        self.name = name
        self.source = source
        self.mode = mode
        self.t_start, self.t_end, self.period = _sta_input_checker(
            t_start, t_end, period)

    def setup(self, spike_times_analysis):
        if self.period:
            t_start, t_end = spike_times_analysis.periods[self.period]
        else:
            t_start, t_end = self.t_start, self.t_end
        st = spike_times_analysis.get(self.source)
        st = strip_st(st)
        st[st < t_start] = float('nan')
        st[st >= t_end] = float('nan')
        self._per_trial = st.apply(lambda x: x.count(), axis=1)
        n_trials = float(st.shape[0])
        n_spikes = float(self._per_trial.sum())
        if self.mode == 'frequency':
            self._result = n_spikes / (n_trials * (t_end - t_start)) * 1000
        elif self.mode == 'count_per_trial':
            self._result = n_spikes / n_trials
        elif self.mode == 'count_total':
            self._result = self._per_trial.sum()


class STAPlugin_extract_column_in_filtered_dataframe(STAPlugin_TEMPLATE):

    def __init__(self, name=None, column_name=None, source=None, select={}):
        if None in (name, column_name, source):
            raise ValueError("name and column and source must be defined!")

        self.name, self.column_name, self.source, self.select = name, column_name, source, select

    def setup(self, spike_times_analysis):
        df = spike_times_analysis.get(self.source)
        df = mdb_utils.select(df, **self.select)
        column = list(df[self.column_name])
        self._result = column


class STAPlugin_spike_times_dataframe(STAPlugin_TEMPLATE):

    def __init__(self,
                 name='spike_times_dataframe',
                 source='spike_times',
                 offset=0,
                 mode='spike_times'):
        self.name = name
        self.source = source
        self.offset = offset
        self.mode = mode

    def setup(self, spike_times_analysis):
        spike_times = spike_times_analysis.get(self.source)
        stim_times = spike_times_analysis.get('stim_times')
        self._result = get_st_from_spike_times_and_stim_times(
            spike_times, stim_times, offset=self.offset, mode=self.mode)


class STAPlugin_response_probability_in_period(STAPlugin_TEMPLATE):

    def __init__(self,
                 name='frequency_in_period',
                 source='st_df',
                 period=None,
                 t_start=None,
                 t_end=None):
        self.name = name
        self.source = source
        self.t_start, self.t_end, self.period = _sta_input_checker(
            t_start, t_end, period)

    def setup(self, spike_times_analysis):
        if self.period:
            t_start, t_end = spike_times_analysis.periods[self.period]
        else:
            t_start, t_end = self.t_start, self.t_end
        st = spike_times_analysis.get(self.source)
        self._by_trial = mdb_analyze_spike_in_interval(st, t_start, t_end)
        self._result = np.mean(self._by_trial)


class STAPlugin_response_latency_in_period(STAPlugin_TEMPLATE):

    def __init__(self,
                 name='frequency_in_period',
                 source='st_df',
                 period=None,
                 t_start=None,
                 t_end=None):
        self.name = name
        self.source = source
        self.t_start, self.t_end, self.period = _sta_input_checker(
            t_start, t_end, period)

    @staticmethod
    def _helper(l_):
        l_ = l_.dropna()
        if len(l_):
            return min(l_)
        else:
            return float('nan')

    @staticmethod
    def _helper_median(l_):
        l_ = l_.dropna()
        if len(l_):
            return np.median(l_)
        else:
            return float('nan')

    def setup(self, spike_times_analysis):
        if self.period:
            t_start, t_end = spike_times_analysis.periods[self.period]
        else:
            t_start, t_end = self.t_start, self.t_end

        st = spike_times_analysis.get(self.source).copy()
        st = strip_st(st)
        st[st < t_start] = float('nan')
        st[st >= t_end] = float('nan')
        self._by_trial = st.apply(self._helper, axis=1)
        self._result = self._helper_median(self._by_trial)


class SpikeTimesAnalysis:
    '''Class for applying event_analysis routines on a spike times dataframe.'''

    def __init__(self,
                 spike_times_object,
                 default_event_analysis=[],
                 periods={}):
        self.periods = periods
        self.spike_times_object = spike_times_object
        # spike_times = _spike_times_series_from_spike_times_dataframe(spike_times_object.st)
        self._db = {}
        try:
            spike_times_object.spike_times
            spike_times_object.stim_times
        except AttributeError:
            pass
        else:
            self._db['spike_times'] = spike_times_object.spike_times
            self._db['stim_times'] = spike_times_object.stim_times
        for ea in default_event_analysis:
            self.apply_extractor(ea)

    def apply_extractor(self, sta_plugin, name=None):
        sta_plugin.setup(self)
        self._db[sta_plugin.name] = sta_plugin

    def get(self, key):
        try:
            return self._db[key]._result
        except AttributeError:
            return self._db[key]

    def get_by_trial(self, key):
        return self._db[key]._by_trial


import six


def get_interval(interval_dict, t):
    for i, v in six.iteritems(interval_dict):
        if (t >= v[0]) and (t < v[1]):
            return i


class VisualizeEventAnalysis:

    def __init__(self, ea):
        self.ea = ea

    def plot_PSTH(self, min_time=0, max_time=2500, bin_size=5):
        st = self.ea.st
        bins = temporal_binning(st, min_time=0, max_time=2500, bin_size=5)
        fig = plt.figure()
        histogram(bins, fig=fig.add_subplot(111))
        ax = fig.axes[-1]
        ax.set_xlabel('t / ms')
        ax.set_ylabel('# spikes / trial / ms')
        ax.set_ylim([0, 0.5])
        sns.despine()
        return fig

    def plot_ISI1_vs_ISI2(self,
                          interval_dict,
                          rp=2.5,
                          color_dict=defaultdict(lambda: 'k'),
                          ax1=None,
                          ax2=None):

        # color_dict = {'ongoing': 'grey', 'onset': 'r', 'sustained': 'k', 'late': 'green', None: 'white'}
        colormap = {
            10: 'r',
            20: 'orange',
            30: 'green',
            40: 'blue',
            50: 'purple'
        }
        e = self.ea.event_db['get_n_bursts']
        tmax = interval_dict['late'][1]
        e = e[e.event_time < tmax]
        if (ax1 is None) or (ax2 is None):
            fig = plt.figure(figsize=(6, 3), dpi=200)
            ax1 = fig.add_subplot(121)
            ax2 = fig.add_subplot(122)

        colors = [
            color_dict[get_interval(interval_dict, t)] for t in e.event_time
        ]
        ax1.scatter(e.ISI_1, e.ISI_2 - e.ISI_1, color=colors, marker='.')
        ax1.set_xlabel('ISI first to second spike')
        ax1.set_ylabel('ISI second to third spike')
        ax1.plot([rp, rp], [0, 100], c='grey')
        ax1.plot([0, 100], [rp, rp], c='grey')
        import six
        for name, c in six.iteritems(colormap):
            if c == 'white':
                continue
            ax1.plot([0, name], [name, 0], c=c, linewidth=.5)

        ax1.set_aspect('equal')
        ax1.set_xlim(0, 30)
        ax1.set_ylim(0, 30)

        import six
        for name, c in six.iteritems(colormap):
            if name > 30:
                continue
            e_filtered = e[(e.ISI_2 < name) & (e.ISI_2 >= name - 10)]
            print(name, len(e_filtered))
            if len(e_filtered) == 0:
                print('skipping')
                continue
            e_filtered.event_time.plot(kind='hist',
                                       bins=np.arange(0, tmax, 1),
                                       cumulative=True,
                                       histtype='step',
                                       color=c,
                                       ax=ax2,
                                       normed=False)
        ax2.set_xlabel('t / ms')
        #ax2.axvline(700, color = 'grey')

        sns.despine()

    def plot(self):
        for k in dir(self):
            if k.startswith('plot_'):
                getattr(self, k)()


############################
# main class for analyzing a spike times file
############################


class AnalyzeFile:

    def __init__(self,
                 path,
                 lim_creast='minimum',
                 lim_trough='minimum',
                 cellid='__no_cellid_assigned__',
                 periods={'1onset': (0, 100)},
                 analogsignal_id=0,
                 stim_times_channel='5',
                 tdelta=1):
        ''' Class for automatic analysis of smr files.
        
        periods: requires '1onset' as key for plot_n_onset function.
        '''
        smr_reader = SmrReader(path,
                               analogsignal_id=analogsignal_id,
                               stim_times_channel=stim_times_channel)
        self.sdct = SpikeDetectionCreastTrough(smr_reader,
                                               lim_creast=lim_creast,
                                               lim_trough=lim_trough,
                                               tdelta=tdelta)
        self.sdct.run_analysis()

        # run event_analysis

        self.ea = EventAnalysis(st)
        df = self.ea.event_db['burst_analysis_2']
        df['experiment'] = cellid
        df['period'] = df.apply(
            lambda x: get_period_label_by_time(self.periods, x.event_time),
            axis=1)
        self.event_df = df

    def get_ongoing_activity(self, period_prestim=30000):
        if self.stim_times[0] < period_prestim:
            s = self.stim_times[0]
            print(
                'warning! there are no {} s activity pre stimulus. Falling back to {}s'
                .format(period_prestim / 1000., s / 1000.))
        else:
            s = period_prestim
        return len([
            t for t in self.spike_times if (t < self.stim_times[0]) and
            (t > self.stim_times[0] - s)
        ]) / (s / 1000.)

    def get_onset_latency(self):
        return np.median([
            s for s in self.st[0]
            if self.periods['1onset'][0] <= s <= self.periods['1onset'][1]
        ])

    def describe(self):
        af = self
        text = 'n trials: {} '.format(af.st.shape[0])
        text += '\n' + 'ongoing activity: {} Hz'.format(
            af.get_ongoing_activity())
        text += '\n' + 'onset spike prob: {}'.format(
            af.get_onset_spike_probability())
        text += '\n' + 'onset spike latency: {} ms'.format(
            af.get_onset_latency())
        text += '\n' + 'creast / trough limit [mV]: {} / {}'.format(
            af.lim_creast, af.lim_trough)
        return text

    def get_onset_spike_probability(self):
        return mdb_analyze_spike_in_interval(self.st, *self.periods['1onset']).mean()

    def _get_fig(self, ax=None):
        if ax is not None:
            return ax
        else:
            fig = plt.figure()
            return fig.add_subplot(111)

    def plot_onset_latency(self, ax=None):
        ax = self._get_fig(ax)
        onset_end = 100  # self.periods['1onset'][1]
        ax.axvspan(*self.periods['1onset'], color='lightgrey')
        ax.hist(self.st[0].dropna().values, bins=np.arange(0, onset_end, 1))
        ax.set_xlabel('onset latency / ms')

    def get_df(self, groupby=['period'], normed=False):

        df = self.event_df

        column_order = [
            'singlet', 'doublet', 'triplet', 'quadruplet', 'quintuplet'
        ]
        _ = df.groupby(groupby).apply(lambda x: x.event_class.value_counts())

        if isinstance(_, pd.Series):  # this happens, if
            _ = _.unstack(-1)
        _ = _.fillna(0)

        if normed:
            _ = _.apply(lambda x: x / x.sum(), axis=1)
        column_order = [c for c in column_order if c in _.columns]
        return _[column_order]

    def get_table(self, groupby=['period']):
        mean_ = self.get_df(groupby, normed=True)
        mean_unnormed = self.get_df(groupby, normed=False)
        return mean_, mean_unnormed

    def plot_burst_fractions(self, ax=None):
        mean_, mean_unnormed = self.get_table()
        ax = self._get_fig(ax)

        d = mean_
        d = d.fillna(0).stack().to_frame(name='n')
        d['period'] = d.index.get_level_values(0)
        d['type'] = d.index.get_level_values(1)

        with pd.option_context("display.max_rows", 1000):
            display.display(mean_.round(2))
            display.display(mean_unnormed.round(2))
        sns.barplot(data=d, x='period', y='n', hue='type', ax=ax)
        ax.set_ylim([0, 1])
        plt.ylabel('% of spiking activity')
        ax.legend()

    def get_n_onset2(self):
        af = self
        tmin, tmax = af.periods['1onset']

        df = af.event_df
        len_ = af.st.shape[0]
        out = pd.Series([0] * len_)

        df = df[(df.event_time >= tmin) & (df.event_time < tmax)]
        df['trial'] = df.trial.str.split('/').str[1].astype(int)
        df = df.set_index('trial')
        out2 = df.event_class.map({
            'singlet': 1,
            'doublet': 2,
            'triplet': 3,
            'quadruplet': 4,
            'quintuplet': 5
        })

        out[out2.index] = out2.values
        return out

    def plot_n_onset(self, ax=None):
        ax = self._get_fig(ax)
        o = self.get_n_onset2().fillna(0)
        o.plot(ax=ax, c='grey', label='__no_legend__', alpha=1, linewidth=.5)
        o.rolling(window=15).mean().plot(ax=ax, alpha=1, linewidth=1, color='k')
        ax.set_ylim(-.5, 4)
        ax.set_xlabel('# trial')
        ax.set_ylabel('# onset spikes')

    def plot_PSTH(self, ax=None):
        ax = self._get_fig(ax)
        ax.set_xlabel('t / ms')
        ax.set_ylabel('# spikes / ms / trial')
        bins = temporal_binning(self.st, min_time=0)
        histogram(bins, fig=ax)

    def plot_all_flat(self):
        af = self
        fig = plt.figure(figsize=(25, 3))
        af.plot_spike_amplitude_histograms(ax=fig.add_subplot(151))
        af.plot_onset_latency(ax=fig.add_subplot(152))
        af.plot_PSTH(ax=fig.add_subplot(153))
        af.plot_burst_fractions(ax=fig.add_subplot(154))
        af.plot_n_onset(ax=fig.add_subplot(155))
        plt.tight_layout()
        sns.despine()

    def plot_all_stacked(self, text=''):
        text = text + self.describe()
        af = self
        fig = plt.figure(figsize=(15, 4))
        ax = fig.add_subplot(231)
        ax.text(0, 0, text)
        ax.axis('off')
        ax.set_ylim(-1, 1)
        af.plot_spike_amplitude_histograms(ax=fig.add_subplot(234))
        af.plot_onset_latency(ax=fig.add_subplot(235))
        af.plot_PSTH(ax=fig.add_subplot(232))
        af.plot_burst_fractions(ax=fig.add_subplot(236))
        af.plot_n_onset(ax=fig.add_subplot(233))
        plt.tight_layout()
        sns.despine()

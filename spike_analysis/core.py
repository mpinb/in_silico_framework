# In Silico Framework
# Copyright (C) 2025  Max Planck Institute for Neurobiology of Behavior - CAESAR

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
# The full license text is also available in the LICENSE file in the root of this repository.

"""
Read and analyze electrophysiological data.
"""

import neo, json, tempfile, shutil, os
from PyPDF2 import PdfFileWriter, PdfFileReader
import json
from functools import partial
import neo
import pandas as pd
import numpy as np
from data_base import utils as db_utils
from collections import defaultdict
import tempfile
import matplotlib.pyplot as plt
import six
from IPython import display
import seaborn as sns
from data_base.analyze.spike_detection import spike_in_interval as db_analyze_spike_in_interval
from data_base.analyze.temporal_binning import universal as temporal_binning
from visualize import histogram
import logging
logger = logging.getLogger("ISF").getChild(__name__)

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
        :py:class:`neo.core.block.Block`: A :py:class:`~neo.core.block.Block` object containing the content of the Spike2 file.
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

    See also:
        :py:class:`spike_analysis.core.ReaderLabView`

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
        """    
        Args:
            path (str): The path to the smr-file.
            analogsignal_id (int): The ID of the analog signal to read.
            stim_times_channel (str): The name of the channel containing the stimulus times.
            min_rel_time (float): The minimum relative time to include in the voltage traces.
            max_rel_time (float): The maximum relative time to include in the voltage traces."""
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
        Get the time points and voltage values of the traces.

        Returns:
            tuple: Two tuples containing the time points and voltage values of the traces respectively.
        '''
        return self.t, self.v

    def get_stim_times(self):
        '''
        Get the times of the stimuli.

        Returns:
            list: A list containing the times of the stimuli.
        '''
        return list(self.stim_times)

    def get_serialize_dict(self):
        '''
        Get a dictionary containing the attributes of the ReaderSmr object.

        Returns:
            dict: A dictionary containing the attributes of the ReaderSmr object:
                    - path (str): The path to the smr-file.
                    - analogsignal_id (int): The ID of the analog signal to read.
                    - stim_times_channel (str): The name of the channel containing the stimulus times.
                    - stim_times (list): The times of the stimuli.
                    - class (str): The class of the object (i.e. ``ReaderSmr``).
                    - min_rel_time (float): The minimum relative time to include in the voltage traces.
                    - max_rel_time (float): The maximum relative time to include in the voltage traces.
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
    '''Not a reader. You provide the data.
    
    :skip-doc:
    '''

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
    """Read in LabView binary data files.
    
    Args:
        path (str): The path to the binary data file.
        scale (int): Scales the data with this value.
        sampling_rate (int): The sampling rate of the data. Used to infer time delta from indices.
    """
    import numpy as np
    with open(path, 'rb') as f:
        while f.read(1) != '\x00':  # skip header
            pass
        data = np.fromfile(
            f, dtype='>f4')  # interpret binary data as big endian float32
    t = [lv * 1. / sampling_rate for lv in range(len(data))]
    return np.array(t) * 1000, data * scale


def highpass_filter(y, sr):
    '''Apply a highpass filter to the data.
    
    Args:
        y (numpy.ndarray): The data to filter.
        sr (int): The sampling rate of the data.
        
    Returns:
        numpy.ndarray: The filtered data.
        
    See also:
        https://dsp.stackexchange.com/questions/41184/high-pass-filter-in-python-scipy
    '''
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
    """A class for reading LabView binary data files and accessing stimulus times and voltage traces.
    
    Data is read using :py:meth:`spike_analysis.core.read_labview_junk1_dat_files`.
    If :paramref:`apply_filter`, a highpass filter is applied to the data using :py:meth:`spike_analysis.core.highpass_filter`.
    
    See also:
        :py:class:`spike_analysis.core.ReaderSmr`
    
    Attributes:
        path (str): The path to the smr-file.
        stim_times (list): The times of the stimuli.
        sampling_rate (int): The sampling rate of the data.
        scale (int): Scales the data with this value.
        apply_filter (bool): Whether to apply a highpass filter to the data.
        t (numpy.ndarray): The time points of the voltage traces.
        v (numpy.ndarray): The voltage values of the traces.
        t_start (float): The start time of the voltage traces.
        t_end (float): The end time of the voltage traces.
    """
    def __init__(
        self,
        path,
        stim_times=None,
        sampling_rate=32000,
        scale=100,
        apply_filter=False
        ):
        """
        Args:
            path (str): The path to the LabView file.
            stim_times (str): list of stimulus times.
            sampling_rate (int): The sampling rate of the data.
            scale (int): Scales the data with this value.
            apply_filter (bool): Whether to apply a highpass filter to the data.
        """
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
        """Get the times of the stimuli.
        
        Returns:
            list: A list containing the times of the stimuli.
        """
        return list(self.stim_times)

    def get_voltage_traces(self):
        """Get the time points and voltage values of the traces.
        
        Returns:
            tuple: Two tuples containing the time points and voltage values of the traces respectively.
        """
        return self.t, self.v

    def get_serialize_dict(self):
        """Get a dictionary containing the attributes of the ReaderLabView object.
        
        Returns:
            dict: A dictionary containing the attributes of the ReaderLabView object:
                    - path (str): The path to the LabView file.
                    - stim_times (list): The times of the stimuli.
                    - sampling_rate (int): The sampling rate of the data.
                    - scale (int): Scales the data with this value.
                    - class (str): The class of the object (i.e. ``ReaderLabView``).
                    - apply_filter (bool): Whether to apply a highpass filter to the data.
        """
        return {
            'path': self.path,
            'stim_times': self.stim_times,
            'sampling_rate': self.sampling_rate,
            'scale': self.scale,
            'class': 'ReaderLabView',
            'apply_filter': self.apply_filter
        }


def load_reader(dict_):
    """Load a reader object from a dictionary.
    
    Args:
        dict_ (dict): A dictionary containing the attributes of the reader object.
        
    Returns:
        object: A reader object.
    
    Raises:
        NotImplementedError: If the class of the reader object is not recognized. Currently, only :py:class:`spike_analysis.core.ReaderSmr` is supported.
    """
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
    '''Filter spike times based on timepoints of detected creasts and troughs. 
    
    A spike is detected by its trough.
    Then, this method checks if there is a corresponding creast at maximum :paramref:`creast_trough_interval` before the trough. 
    All creasts fullfilling this criterion are extracted. 
    The spike time is set to the latest creast (if :paramref:`mode` = ``latest``) or the maximum creast amplitude (if :paramref:`mode` = ``creast_max``). 
    
    If a through does not have a corresponding creast, no spike is detected.
    
    Args:
        spike_times (list): list containing spike times defined by the creast of the waveform
        spike_times_trough (list): list containing spike times defined by the trough of the waveform
    
    Returns:
        filtered_spike_times: list, containing spikes fullfilling the definition above.
    '''
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
    """Filters out any events that occur in an interval shorter than tdelta.

    Args:
        t (list): A list containing timepoints of events.
        tdelta (float, optional): Minimal interval between events. Defaults to 0.

    Returns:
        list: A list containing filtered spike times.

    Example:
    
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
    Assumption: The stimulus interval is constant.
    
    :skip-doc:
    '''
    return stim_times[1] - stim_times[0]


def stimulus_interval_filter(stim_times, period_length=1, offset=0):
    """Filters periodic stimuli such that only the first stimulus of each period is retained.

    Args:
        stim_times (list): A list containing stimulus times.
        period_length (int, optional): The number of stimuli forming one period. Defaults to 1.
        offset (int, optional): The number of the stimulus in each period to be extracted. Defaults to 0.

    Returns:
        list: A list containing filtered stimulus times.

    Example:
    
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

def get_st_from_spike_times_and_stim_times(
    spike_times,
    stim_times,
    offset = 0,
    mode = 'spike_times'
    ):
    """Computes spike times dataframe based on list of spike times and stimulus times.

    Args:
        spike_times (list): List of spike times.
        stim_times (list): List of stimulus times.
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
    """Get a DataFrame containing only spike times, without metadata.
    
    Filters out all columns that cannot be converted to an integer.
    
    Args:
        st: A pandas DataFrame containing spike times as generated by get_st_from_spike_times_and_stim_times
    
    Returns:
        pd.DataFrame: A DataFrame containing only spike times.
    """
    return st[[c for c in st.columns if db_utils.convertible_to_int(c)]]



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
    
    Attributes:
        lim_creast (float|str): lim_creast used for spike detection (if "minimum" or "zero" was defined, this will be the numeric value used)
        lim_trough (float|str): lim_trough used for spike detection (if "minimum" or "zero" was defined, this will be the numeric value used)
        st (pd.DataFrame): spike times dataframe, one row per trial
        spike_times (list): all extracted spike times, fullfilling creast and trough criterion, filtered such thatthe minimal ISI is above tdelta.
        _spike_times_creast (list): spike times fullfilling creast criterion
        _spike_times_trough (list): spike times fullfilling trough criterion
    '''

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
        """
        Args:
            reader_object (:py:class:`~spike_analysis.core.ReaderSmr`|:py:class:`~spike_analysis.core.LabViewReader`): 
                Reader object with get_voltage_traces and get_stim_times method, e.g. ReaderSmr
            lim_creast (float|str) 
                threshold above which a creast of a spike is detected as such. 
                Needs to be float, ``"minimum"``, or ``"zero"``. 
                If "minimum" or "zero" is chosen, the threashold will be set based on the histogram of all creasts. 
                If "minimum" is chosen, :paramref:`lim_creast` will be set to the first minimum in the histogram above or equal to :math:`0.4mV`. 
                If "zero" is chosen, :paramref:`lim_creast` will be set to the first empty bin.
            lim_trough (float|str) as :paramref:`lim_creast`. If float is specified, you probably 
                want to use a negative value. lim creast and lim_trough need to be both floats, both 
                "zero" or both "minimum".
            max_creast_trough_interval (float): Maximum interval between creast and trough such that a spike is recognized.
            tdelta (float): minimum interval between spikes
            stimulus_period (int): number of stimuli applied per trial. E.g., for paired pulse stimuli, it should be 2.
            stimulus_period_offse (int): Number of stimulus that initiates first trial.
            cellid (str): name to be used in spike times dataframe
        """
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
        """Runs the spike detection analysis.
        
        Wrapper function to run the spike detection analysis.
        
        See also:
            :py:meth:`~spike_analysis.core.SpikeDetectionCreastTrough._extract_spike_times`
        """
        self._extract_spike_times()

    def _set_creast_trough(self, lim_creast, lim_trough):
        """Sets the creast and trough limits based on the given values.
        
        Args:
            lim_creast (float|str): Threshold above which a creast of a spike is detected as such. 
            lim_trough (float|str): Threshold below which a trough of a spike is detected as such.
            
        Raises:
            ValueError: If lim_creast and lim_trough are not both floats or both "minimum" or both "zero".
            
        See also:
            :py:meth:`~spike_analysis.core.SpikeDetectionCreastTrough.get_creast_and_trough_ampltidues_by_bins`
            
        Returns:
            None. Sets the :paramref:`lim_creast` and :paramref:`lim_trough` attributes.
        """
        # automatic detection of creast and trough limit
        if lim_creast == 'minimum' and lim_trough == 'minimum':
            lim_creast, lim_trough = self.get_creast_and_trough_ampltidues_by_bins('minimum')
        elif lim_creast == 'zero' and lim_trough == 'zero':
            lim_creast, lim_trough = self.get_creast_and_trough_ampltidues_by_bins('zero')
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
        """Extracts spike times from voltage traces.
        
        Extracts spike times based on creast and trough amplitude.
        Only returns spike times that fullfill both the creast and trough criterion and have an ISI above :paramref:`tdelta`.
        Spikes that only fullfill the creast criterion are stored in :paramref:`_spike_times_creast`, and similarly for the trough criterion.
        
        Returns:
            list: A list containing spike times.
        """
        # aliases
        t, v = self.reader.get_voltage_traces()
        lim_creast, lim_trough = self.lim_creast, self.lim_trough
        tdelta = self.tdelta
        upper_creast_threshold = self.upper_creast_threshold
        
        # spike times detected by creast
        a, b = get_peaks_above(t, v, lim_creast)
        self._spike_times_creast, self._spike_amplitudes_creast = a, np.array(b)
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
        """Get the creast and trough amplitudes based on the histogram of the creasts and troughs.
        
        Args:
            mode (str): Mode of computation. Can be 'zero' or 'minimum'. Defaults to 'zero'.
            
        Returns:
            tuple: A tuple containing the creast and trough amplitudes.
        """
        # aliases
        t, v = self.reader.get_voltage_traces()
        t, v = np.array(t), np.array(v)

        if len(self.stim_times) < 2:
            logger.info("Less than 2 stimuli found. using whole trace to determine lim_creast and lim_trough.")
        else:
            logger.info("Using interval between first stimlus and last stimulus to determine lim_creast and lim_trough.")
            index = (self.stim_times[0] < t) & (t < self.stim_times[-1])
            t = t[index]
            v = v[index]

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
        else:
            raise ValueError("mode must be 'zero' or 'minimum'")
        return minimun_zero_bin_st, minimun_zero_bin_sst * -1

    def get_default_events(
        self,
        show_stim_times=True,
        show_trough_candidates=True):
        '''Returns a list of events to be displayed with the :py:meth:`~spike_analysis.core.SpikeDetectionCreastTrough.show_events` method.
        
        Creates events for deteced spikes (black line) and spike candidates [dotted black line]
        (i.e. creasts and troughs exceeding the limit but which do not qualify to 
        be a spike)
        
        Args:
            show_stim_times: Show the stimulus times in addition to the detected spikes.
            show_trough_candidates: Show trough candidates in addition to the detected spikes.
        
        Returns:
            events (list): list containing 4-tuples of the format (time, color, linestyle, linewidth)
                Spike times are pink, spike candidates are black, stimulus times are red.
        '''
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
        '''Shows voltage trace, thresholds and events.
        
        Events are spike times, spike candidates, and stimulus times.
        Spike times are shown as pink line, spike candidates as black dotted line, stimulus times as red line.
        
        Args:
            events (str|list):
                'auto': uses :py:meth:`~spike_analysis.core.SpikeDetectionCreastTrough.get_default_events` to show events.
                'only_creast': Does not show trough candidates.
                list: explicitly define events to show. Needs to be list containing 4-touples in the following format: ``(timepoint, 'color', 'linestyle', linewidth)``
            savepdf (str): If specified, saves the figure to the given path.
            showfig (bool): If True, displays the figure.
            ylim (tuple): y-axis limits of the plot.
            
        Raises:
            ValueError: If events is not 'auto', 'only_creast', or a list.
            
        Returns:
            None
        
        See also:
            :py:meth:`~spike_analysis.core.SpikeDetectionCreastTrough.get_default_events`
        '''
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
        """Get a dictionary containing the attributes of the SpikeDetectionCreastTrough object.
        
        Returns:
            dict: 
                A dictionary containing the attributes of the SpikeDetectionCreastTrough object:
                    
                - reader_object (dict): A dictionary containing the attributes of the reader object.
                - lim_creast (float): The threshold above which a creast of a spike is detected as such.
                - lim_trough (float): The threshold below which a trough of a spike is detected as such.
                - max_creast_trough_interval (float): The maximum interval between creast and trough such that a spike is recognized.
                - tdelta (float): The minimum interval between spikes.
                - stimulus_period (int): The number of stimuli applied per trial.
                - stimulus_period_offset (int): The number of the stimulus in each period to be extracted.
                - stim_times (list): A list containing stimulus times.
                - cellid (str): The name to be used in the spike times dataframe.
                - spike_times (list): A list containing spike times.
                - _spike_times_creast (list): A list containing spike times fullfilling the creast criterion.
                - _spike_times_trough (list): A list containing spike times fullfilling the trough criterion.
                - t_start (float): The start time of the voltage traces.
                - t_end (float): The end time of the voltage traces.
        """
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
        """Saves the SpikeDetectionCreastTrough object to a JSON file."""
        with open(path, 'w') as out:
            json.dump(self.get_serialize_dict(), out)

    @staticmethod
    def load(path, init_reader=False):
        """Loads a SpikeDetectionCreastTrough object from a JSON file.
        
        Args:
            path (str): The path to the JSON file.
            init_reader (bool, optional): If True, initializes the reader object. Defaults to False.
        """
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
        """skip-doc:"""
        pass  # todo


#################################################
# classify timepoint at which a spike occurs
#################################################
def get_period_label_by_time(periods, t):
    '''Classifies timepoint based on whether it falls within a period.
    
    Args:
        periods (dict): dictionary containing period label as key and (period_start, period_end) as value
        t (float): timepoint to classify
    
    Returns:
        str: label of period in which t is in. 'undefined' if t is in no defined period
    '''
    import six
    for k, (tmin, tmax) in six.iteritems(periods):
        if tmin <= t < tmax:
            return k
    return 'undefined'


#################################################
# methods for analyzing events (doublets, bursts)
#################################################


def _spike_times_series_from_spike_times_dataframe(st):
    '''Converts a spike times dataframe to a pd.Series.
    
    The series has the following format:
        keys: same as keys in st
        values: list of spike times, as in st, but without NaN and metadata.
        
    :skip-doc:
    '''
    st = strip_st(st)
    dummy = [
        (name, get_spike_times_from_row(row)) for name, row in st.iterrows()
    ]
    spike_times = pd.Series([d[1] for d in dummy],
                              index=[d[0] for d in dummy])
    return spike_times


def _sta_apply_helper(spike_times, analysis_function, periods={}):
    '''
    
    :skip-doc:
    
    helper function for applying an analysis_function on spike_times in
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
    """Checks if the input is valid.
    
    Args:
        t_start (float): Start time.
        t_end (float): End time.
        period (dict): Dictionary containing period labels as keys and (period_start, period_end) as values.
        
    Returns:
        tuple: A tuple containing the start time, end time, and period.
    
    Raises:
        ValueError: If both :paramref:`period` and either :paramref:`t_start` or :paramref:`t_end` are defined.
        ValueError: If only one of :paramref:`t_start` or :paramref:`t_end` is defined.
    """
    errstr = 'You can define period or t_start and t_end, but not both.'
    if period:
        if t_start or t_end:
            raise ValueError(errstr)
    if t_start or t_end:
        if not t_start and t_end:
            raise ValueError(errstr)
    return t_start, t_end, period


class STAPlugin_TEMPLATE(object):
    """Base class for spike time analysis plugins.
    
    Attributes:
        _result: The result of the analysis.
    """
    def __init__(self):
        self._result = None

    def get_result(self):
        """Gets the result of the analysis.
        
        The result and data format of the analysis depends on which type of analysis is performed.
        
        Returns:
            Any: The result of the analysis.
            
        Raises:
            RuntimeError: If the result is requested before :py:meth:`~spike_analysis.core.STAPlugin_TEMPLATE.setup` is called.
        """
        if self._result is None:
            raise RuntimeError("You need to call setup first")
        else:
            return self._result

    def setup(self):
        """Sets up the analysis.
        
        This method needs to be overwritten by the subclass.
        """
        raise NotImplementedError


class STAPlugin_ISIn(STAPlugin_TEMPLATE):
    """SpikeTimeAnalysis (STA) plugin to compute the inter spike interval (ISI) to the next, second next, nth spike.
        
    See also:
        :py:class:`spike_analysis.core.SpikeTimesAnalysis` reads in :paramref:`source`.
        
    Attributes:
        name (str): The name of the plugin.
        source (str): The :py:class:`~data_base.data_base.DataBase` key containing the spike times.
        max_n (int): The maximum order of ISIs computed.
    """
    def __init__(self, name='ISIn', source='spike_times', max_n=5):
        """
        Args:
            name (str, optional): The name of the plugin. Defaults to 'ISIn'.
            source (str, optional): The :py:class:`~data_base.data_base.DataBase` key containing the spike times. Defaults to 'spike_times'.
            max_n (int, optional): The maximum order of ISIs computed. Defaults to 5."""
        self.name = name
        self.source = source
        self.max_n = max_n
        STAPlugin_TEMPLATE.__init__(self)

    def setup(self, spike_times_analysis):
        """Sets up the analysis: Computes the inter spike interval (ISI) to the next, second next, nth spike.
        
        :paramref:`_result` will be a pd.DataFrame containing the columns ``ISI_1`` to ``ISI_n``, and event_time.
        
        Args:
            spike_times_analysis (:py:class:`~spike_analysis.core.SpikeTimesAnalysis`): The spike times analysis object.
            
        See also:
            :py:meth:`~spike_analysis.core.STAPlugin_TEMPLATE.get_result`
        """
        times = spike_times_analysis.get(self.source)
        self._result = self.event_analysis_ISIn(times, self.max_n)

    @staticmethod
    def event_analysis_ISIn(spike_times, n=5):
        '''Computes for each spike the inter spike interval (ISI) to the next, second next ... nth next spike.
        
        Args:
            spike_times (list): list, containing spike times
            n (int): Max order of ISIs computed (e.g. if n = 1, only the interval between each spike and the first next spike will be computed)
        
        Returns:
            pd.DataFrame: dataframe containing the columns ``ISI_1`` to ``ISI_n``, and event_time
                The ``ISI_n`` columns contain the time interval between the current spike (@ event time) 
                and the nth next spike. ``np.NaN`` if there is no nth next spike.
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
    """SpikeTimeAnalysis (STA) plugin to detect high frequency events (doublet, triplet, ...) that occur within a timewindow.
    
    See also:
        :py:class:`spike_analysis.core.SpikeTimesAnalysis` reads in :paramref:`source`.
        
    Attributes:
        name (str): The name of the plugin.
        source (str, optional): The :py:class:`~data_base.data_base.DataBase` key containing the spike times. Defaults to 'spike_times'.
        event_maxtimes (dict): Dictionary containing the maximum duration of each event type.
        event_names (dict): Dictionary containing the names of the event types.
    """
    def __init__(
        self,
        name='bursts',
        source='spike_times',
        event_maxtimes=None,
        event_names=None
        ):
        """
        Args:
            name (str, optional): The name of the plugin. Defaults to 'bursts'.
            source (str, optional): The :py:class:`~data_base.data_base.DataBase` key containing the spike times. Defaults to 'spike_times'.
            event_maxtimes (dict, optional): Dictionary containing the maximum duration of each event type. Default: ``{0:0, 1:10, 2:30}``
            event_names (dict, optional): Dictionary containing the names of the event types. Default: ``{0: "singlet", 1: "doublet", 2: "triplet"}``"""
        if event_maxtimes is None:
            event_maxtimes = {0:0, 1:10, 2:30}
        if event_names is None:
            event_names = {0: 'singlet',1: 'doublet',2: 'triplet'}
        STAPlugin_TEMPLATE.__init__(self)
        self.name = name
        self.source = source
        self.event_maxtimes = event_maxtimes
        self.event_names = event_names

    def setup(self, spike_times_analysis):
        """Sets up the analysis: Detects high frequency events (doublet, triplet, ...) that occur within a timewindow.
        
        :paramref:`_result` will be a pd.DataFrame containing the annotated dataframe containing the event times, classes and interspike intervals.
        
        Args:
            spike_times_analysis (:py:class:`~spike_analysis.core.SpikeTimesAnalysis`): The spike times analysis object.
            
        See also:
            :py:meth:`~spike_analysis.core.STAPlugin_TEMPLATE.get_result`
        """
        times = spike_times_analysis.get(self.source)
        self._result = self.event_analysis_bursts(times, self.event_maxtimes,self.event_names)

    @staticmethod
    def event_analysis_bursts(row, event_maxtimes=None, event_names=None):
        '''Detects high frequency events (doublet, triplet, ...) that occur within a timewindow.
        
        An event is always classified as the one with the highest number of spikes possible,
        E.g., [1, 5, 9] could be classified as doublet + singlet, but it will be a triplet.
        
        Args:
            row (list-like): Contains spike times.
            event_maxtimes (dict): Dictionary where keys indicate event type (0 means singlet, 1 means doublet, 2 means triplet, ...),
                and values indicate max duration of such an event.
            event_name (dict): Dictionary with names of the events (0: 'singlet', 1: 'doublet', 2: 'triplet').
        
        Returns:
            pandas.DataFrame: One row per event. Columns are:
                - event_time: Timepoint of the first spike belonging to the event.
                - event_class: Class of event as defined in event_name.
                - ISI_{n}: Interval from the first spike of the event to the nth spike of the event.
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
    """SpikeTimeAnalysis (STA) plugin to annotate bursts in a spike times dataframe.
    
    See also:
        :py:class:`spike_analysis.core.SpikeTimesAnalysis` reads in :paramref:`source`.
        
    Attributes:
        name (str): The name of the plugin.
        source (str, optional): The :py:class:`~data_base.data_base.DataBase` key containing the spike times. Defaults to 'spike_times'.
        event_maxtimes (dict): Dictionary containing the maximum duration of each event type.
        event_names (dict): Dictionary containing the names of the event types.
    """
    def __init__(self,
                 name='bursts_st',
                 source='st',
                 event_maxtimes=None,
                 event_names=None):
        """    
        Args:
            name (str, optional): The name of the plugin. Defaults to 'bursts_st'.
            source (str, optional): The :py:class:`~data_base.data_base.DataBase` key containing the spike times. Defaults to 'spike_times'.
            event_maxtimes (dict, optional): Dictionary containing the maximum duration of each event type. Default: ``{0:0, 1:10, 2:30}``
            event_names (dict, optional): Dictionary containing the names of the event types. Default: ``{0: "singlet", 1: "doublet", 2: "triplet"}``"""
        if event_maxtimes is None:
            event_maxtimes = {0:0, 1:10, 2:30}
        if event_names is None:
            event_names = {0: 'singlet',1: 'doublet',2: 'triplet'}
        self.name = name
        self.source = source
        self.event_maxtimes = event_maxtimes
        self.event_names = event_names

    def setup(self, spike_times_analysis):
        """Sets up the analysis: annotates bursts in a spike times dataframe.
        
        :paramref:`_result` will be a pd.DataFrame containing the annotated spike times dataframe.
        
        Args:
            spike_times_analysis (:py:class:`~spike_analysis.core.SpikeTimesAnalysis`): The spike times analysis object.
            
        See also:
            :py:meth:`~spike_analysis.core.STAPlugin_TEMPLATE.get_result`
        """
        st = spike_times_analysis.get(self.source)
        st = strip_st(st)

        dfs = [
            STAPlugin_bursts.event_analysis_bursts(
                row.dropna(),
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
    """SpikeTimeAnalysis (STA) plugin to compute the ongoing activity.
    
    See also:
        :py:class:`spike_analysis.core.SpikeTimesAnalysis` reads in :paramref:`source`.

    Attributes:
        name (str): The name of the plugin. Defaults to 'ongoing_activity'.
        source (str, optional): The :py:class:`~data_base.data_base.DataBase` key containing the spike times. Defaults to 'spike_times'.
        ongoing_sample_length (int): The length of the ongoing sample in ms. Defaults to 90000.
        mode (str): The mode of the analysis. Can be 'frequency' or 'count'. Defaults to 'frequency'.
    """
    def __init__(self,
                 name='ongoing_activity',
                 source='spike_times',
                 ongoing_sample_length=90000,
                 mode='frequency'):
        """
        Args:
            name (str, optional): The name of the plugin. Defaults to 'ongoing_activity'.
            source (str, optional): The :py:class:`~data_base.data_base.DataBase` key containing the spike times. Defaults to 'spike_times'.
            ongoing_sample_length (int, optional): The length of the ongoing sample in ms. Defaults to 90000.
            mode (str, optional): The mode of the analysis. Can be 'frequency' or 'count'. Defaults to 'frequency'. 
        """
        STAPlugin_TEMPLATE.__init__(self)
        if not mode in ('frequency', 'count'):
            raise ValueError('mode must be "frequency" or "count"!')
        self.name = name
        self.source = source
        self.ongoing_sample_length = ongoing_sample_length
        self.mode = mode

    def setup(self, spike_times_analysis):
        """Sets up the analysis: calculates the ongoing activity.
        
        :paramref:`_result` will be the ongoing activity.
        
        Args:
            spike_times_analysis (:py:class:`~spike_analysis.core.SpikeTimesAnalysis`): The spike times analysis object.
            
        See also:
            :py:meth:`~spike_analysis.core.STAPlugin_TEMPLATE.get_result`
        """
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
    """SpikeTimeAnalysis (STA) plugin to quantify the activity in a period.
        
    Attributes:
        name (str): The name of the plugin. Defaults to 'frequency_in_period'.
        source (str): The :py:class:`~data_base.data_base.DataBase` key containing the spike times.
        period (str): The period to analyze.
        t_start (float): The start time of the period.
        t_end (float): The end time of the period.
        mode (str): The mode of the analysis. Can be 'frequency', 'count_per_trial', or 'count_total'.   
    """
    def __init__(self,
                 name='frequency_in_period',
                 source='st_df',
                 period=None,
                 t_start=None,
                 t_end=None,
                 mode='frequency'):
        """
        Args:
            name (str, optional): The name of the plugin. Defaults to 'frequency_in_period'.
            source (str, optional): The :py:class:`~data_base.data_base.DataBase` key containing the spike times. Defaults to 'st_df'.
            period (str, optional): The period to analyze. Defaults to None (entire trace).
            t_start (float, optional): The start time of the period. Defaults to None.
            t_end (float, optional): The end time of the period. Defaults to None.
        """
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
        """Sets up the analysis: quantifies the activity in a period.
        
        :paramref:`_result` will be the quantified activity. This is either:
        
        - the frequency of the activity in the period (mode='frequency')
        - the count of the activity per trial (mode='count_per_trial')
        - the total count of the activity (mode='count_total')
        
        See also:
            :py:meth:`~spike_analysis.core.STAPlugin_TEMPLATE.get_result`
        """
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
    """SpikeTimeAnalysis (STA) plugin to extract a column from a filtered dataframe.
    
    Raises:
        ValueError: If :paramref:`name`, :paramref:`column_name`, or :paramref:`source` are not defined.
        
    See also:
        :py:class:`spike_analysis.core.SpikeTimesAnalysis` reads in :paramref:`source`.

    See also:
        :py:meth:`data_base.utils.select` filters out the columns using :paramref:`select`
        
    Attributes:
        name (str): The name of the plugin.
        column_name (str): The name of the column to extract.
        source (str): The :py:class:`~data_base.data_base.DataBase` key containing the dataframe.
        select (dict): The selection criteria for the dataframe.
    """

    def __init__(self, name=None, column_name=None, source=None, select={}):
        """
        Args:
            name (str, optional): The name of the plugin. Defaults to None.
            column_name (str, optional): The name of the column to extract. Defaults to None.
            source (str, optional): The :py:class:`~data_base.data_base.DataBase` key containing the dataframe. Defaults to None. 
        """
        if None in (name, column_name, source):
            raise ValueError("name and column and source must be defined!")
        self.name, self.column_name, self.source, self.select = name, column_name, source, select

    def setup(self, spike_times_analysis):
        """Sets up the analysis: extracts a column from a filtered dataframe.
        
        :paramref:`_result` will be the extracted column.
        
        Args:
            spike_times_analysis (:py:class:`~spike_analysis.core.SpikeTimesAnalysis`): The spike times analysis object.
            
        See also:
            :py:meth:`~spike_analysis.core.STAPlugin_TEMPLATE.get_result`
        """
        df = spike_times_analysis.get(self.source)
        df = db_utils.select(df, **self.select)
        column = list(df[self.column_name])
        self._result = column


class STAPlugin_spike_times_dataframe(STAPlugin_TEMPLATE):
    """SpikeTimeAnalysis (STA) plugin to create a spike times dataframe.
        
    See also:
        :py:class:`spike_analysis.core.SpikeTimesAnalysis` reads in :paramref:`source`.
 
    Attributes:
        name (str): The name of the plugin.
        source (str): The :py:class:`~data_base.data_base.DataBase` key containing the spike times.
        offset (int): The offset of the spike times.
        mode (str): The mode of the analysis. Can be 'spike_times' or 'stim_times'.
    """
    def __init__(self,
                 name='spike_times_dataframe',
                 source='spike_times',
                 offset=0,
                mode='spike_times'):
        """
        Args:
            name (str, optional): The name of the plugin. Defaults to 'spike_times_dataframe'.
            source (str, optional): The :py:class:`~data_base.data_base.DataBase` key containing the spike times. Defaults to 'spike_times'.
            offset (int, optional): The offset of the spike times. Defaults to 0.
            mode (str, optional): The mode of the analysis. Can be 'spike_times' or 'stim_times'. Defaults to 'spike_times'.
        """
        self.name = name
        self.source = source
        self.offset = offset
        self.mode = mode

    def setup(self, spike_times_analysis):
        """Sets up the analysis: creates a spike times dataframe.
        
        :paramref:`_result` will be the spike times dataframe.
        
        Args:
            spike_times_analysis (:py:class:`~spike_analysis.core.SpikeTimesAnalysis`): The spike times analysis object.
            
        See also:
            :py:meth:`~spike_analysis.core.STAPlugin_TEMPLATE.get_result`
        """
        spike_times = spike_times_analysis.get(self.source)
        stim_times = spike_times_analysis.get('stim_times')
        self._result = get_st_from_spike_times_and_stim_times(
            spike_times, stim_times, offset=self.offset, mode=self.mode)


class STAPlugin_response_probability_in_period(STAPlugin_TEMPLATE):
    """SpikeTimeAnalysis (STA) plugin to compute the response probability in a period.
    
    See also:
        :py:class:`spike_analysis.core.SpikeTimesAnalysis` reads in :paramref:`source`.
        
    Attributes:
        name (str): The name of the plugin. Defaults to 'frequency_in_period'.
        _by_trial (:py:class:`numpy.ndarray`): Whether there are any spikes in this trial.
    """
    def __init__(
        self,
        name='frequency_in_period',
        source='st_df',
        period=None,
        t_start=None,
        t_end=None):
        """
        Args:
            name (str, optional): The name of the plugin. Defaults to 'frequency_in_period'.
            source (str, optional): The :py:class:`~data_base.data_base.DataBase` key containing the spike times. Defaults to 'st_df'.
            period (str, optional): The period to analyze. Defaults to None (entire trace).
            t_start (float, optional): The start time of the period. Defaults to None.
            t_end (float, optional): The end time of the period. Defaults to None.
        """
        self.name = name
        self.source = source
        self.t_start, self.t_end, self.period = _sta_input_checker(
            t_start, t_end, period)

    def setup(self, spike_times_analysis):
        """Sets up the analysis: computes the response probability in a period.
        
        :paramref:`_result` will be the response probability.
        
        Args:
            spike_times_analysis (:py:class:`~spike_analysis.core.SpikeTimesAnalysis`): The spike times analysis object.
            
        See also:
            :py:meth:`~spike_analysis.core.STAPlugin_TEMPLATE.get_result`
        """
        if self.period:
            t_start, t_end = spike_times_analysis.periods[self.period]
        else:
            t_start, t_end = self.t_start, self.t_end
        st = spike_times_analysis.get(self.source)
        self._by_trial = db_analyze_spike_in_interval(st, t_start, t_end)
        self._result = np.mean(self._by_trial)


class STAPlugin_response_latency_in_period(STAPlugin_TEMPLATE):
    """SpikeTimeAnalysis (STA) plugin to compute the response latency in a period.
            
    See also:
        :py:class:`spike_analysis.core.SpikeTimesAnalysis` reads in :paramref:`source`.
 
    Attributes:
        name (str): The name of the plugin. Defaults to 'frequency_in_period'.
        _by_trial (:py:class:`numpy.ndarray`): The median response latency by trial.
    """
    def __init__(
        self,
        name='frequency_in_period',
        source='st_df',
        period=None,
        t_start=None,
        t_end=None):
        """
        Args:
            name (str, optional): The name of the plugin. Defaults to 'frequency_in_period'.
            source (str, optional): The :py:class:`~data_base.data_base.DataBase` key containing the spike times. Defaults to 'st_df'.
            period (str, optional): The period to analyze. Defaults to None (entire trace).
            t_start (float, optional): The start time of the period. Defaults to None.
            t_end (float, optional): The end time of the period. Defaults to None.
        """
        self.name = name
        self.source = source
        self.t_start, self.t_end, self.period = _sta_input_checker(
            t_start, t_end, period)

    @staticmethod
    def _helper(l_):
        """:skip-doc:"""
        l_ = l_.dropna()
        if len(l_):
            return min(l_)
        else:
            return float('nan')

    @staticmethod
    def _helper_median(l_):
        """:skip-doc:"""
        l_ = l_.dropna()
        if len(l_):
            return np.median(l_)
        else:
            return float('nan')

    def setup(self, spike_times_analysis):
        """Sets up the analysis: computes the response latency in a period.
        
        :paramref:`_result` will be the response latency.
        
        Args:
            spike_times_analysis (:py:class:`~spike_analysis.core.SpikeTimesAnalysis`): The spike times analysis object.
            
        See also:
            :py:meth:`~spike_analysis.core.STAPlugin_TEMPLATE.get_result`
        """
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
    '''Class for applying event_analysis routines on a spike times dataframe.
        
    Attributes:
        spike_times_object (object): The spike times object.
        _db (dict): The database containing the spike times and the event analysis routines.
        periods (dict): A dictionary containing period labels as keys and (period_start, period_end) as values.
    '''

    def __init__(
        self,
        spike_times_object,
        default_event_analysis=[],
        periods={}):
        """
        Args:
            spike_times_object (object): The spike times object.
            default_event_analysis (list): A list of event analysis routines.
            periods (dict): A dictionary containing period labels as keys and (period_start, period_end) as values.
        """
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
        """Applies an event analysis routine.
        
        Args:
            sta_plugin (object): The event analysis routine.
        """
        sta_plugin.setup(self)
        self._db[sta_plugin.name] = sta_plugin

    def get(self, key):
        """Get a key from the database.
        
        If the key refers to a STAPlugin, the result of the analysis is returned.
        Otherwise, the corresponding value is returned.
        
        Args:
            key (str): The name of the event analysis routine.
        """
        try:
            return self._db[key]._result
        except AttributeError:
            return self._db[key]

    def get_by_trial(self, key):
        """Get spike information by trial.
        
        Assumes the key refers to an STAPlugin that contains the attribute ``_by_trial``.
        
        Args:
            key (str): The name of the event analysis routine, referring to an STAPlugin.
        
        Example:
            :py:class:`~spike_analysis.core.STAPlugin_response_probability_in_period` and
            :py:class:`~spike_analysis.core.STAPlugin_response_latency_in_period` have this attribute.
        """
        return self._db[key]._by_trial




def get_interval(interval_dict, t):
    """:skip-doc:
    
    used in :py:class:`~spike_analysis.core.VisualizeEventAnalysis`, which
    seems deprecated?
    """
    for i, v in six.iteritems(interval_dict):
        if (t >= v[0]) and (t < v[1]):
            return i


class VisualizeEventAnalysis:
    """Todo: this seems deprecated.
    
    What are the EventAnalysis objects?
    What are their .st attributes?
    
    :skip-doc:"""

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
    """Todo: what is the usecase of this class?
    
    The names of the readers have been changed. Whats the EventAnalysis object?
    
    :skip-doc:
    """
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
        smr_reader = ReaderSmr(path,
                               analogsignal_id=analogsignal_id,
                               stim_times_channel=stim_times_channel)
        self.sdct = SpikeDetectionCreastTrough(smr_reader,
                                               lim_creast=lim_creast,
                                               lim_trough=lim_trough,
                                               tdelta=tdelta)
        self.sdct.run_analysis()

        # run event_analysis

        self.ea = SpikeTimesAnalysis(self.sdct)
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
        return db_analyze_spike_in_interval(self.st, *self.periods['1onset']).mean()

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

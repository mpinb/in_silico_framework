from .context import *
from spike_analysis.core import *
import numpy as np
import pandas as pd

class _TestSpikeTimes:
    def __init__(self, t=[], v=[], stim_times=[], spike_times=[]):
        self.t = t
        self.v = v
        self.stim_times = stim_times
        self.spike_times = spike_times
        self.t_start=0
        self.t_end=200
        
    def get_voltage_traces(self):
        return I.np.array(self.t), I.np.array(self.v)
    
    def get_stim_times(self):
        return self.stim_times
    
    
class Tests:
    def test_can_load_smr_file(self):
        read_smr_file(test_smr_path)
    
    def test_get_peaks_above(self):
        t = [.0,.1,.2,.3,.4,.5,.6,.7,.8]
        v = [0,  1, 2, 1, 3, 4, 3, 4, 5]
        t_res, v_res = get_peaks_above(t,v, 0.5)
        np.testing.assert_almost_equal(t_res, [0.2, .5])
        np.testing.assert_almost_equal(v_res, [2, 4])
        t_res, v_res = get_peaks_above(t,v, 2)
        np.testing.assert_almost_equal(t_res, [0.2, .5])
        np.testing.assert_almost_equal(v_res, [2, 4])      
        t_res, v_res = get_peaks_above(t,v, 3)
        np.testing.assert_almost_equal(t_res, [.5])
        np.testing.assert_almost_equal(v_res, [4]) 
            
    def test_filter_spike_times(self):
        sta = np.array([1])
        assert not any(filter_spike_times([],[], spike_times_amplitude=sta))
        assert not any(filter_spike_times([],[10], spike_times_amplitude=sta))
        assert filter_spike_times([8],[10], spike_times_amplitude=sta) == (np.array([8]), np.array([1]))
        assert not any(filter_spike_times([8],[], spike_times_amplitude=sta))
        
        sta = np.array([1, 1, 1])
        for spike_times_trough in [[10], [10, 10.1], [10, 10.1, 10.2]]:
            l = len(spike_times_trough)
            st, ampl = filter_spike_times([8, 8.1, 8.2], spike_times_trough, spike_times_amplitude=sta)
            assert all(st == np.array(l*[8.2]))
            assert all(ampl == np.array(l*[1]))
                
    def test_filter_short_ISIs(self):
        spike_times = [0,1,2,3,4,5,6,7,8]
        assert filter_short_ISIs(spike_times, tdelta=1) == spike_times
        assert filter_short_ISIs(spike_times, tdelta=1.1) == [0,2,4,6,8]
        assert filter_short_ISIs(spike_times, tdelta=2) == [0,2,4,6,8]
        assert filter_short_ISIs([], tdelta=2) == []
        assert filter_short_ISIs(spike_times, tdelta=10) == [0]
        
    def test_stimulus_interval_filter(self):
        assert stimulus_interval_filter([1,2,3,4]) == [1,2,3,4]
        assert stimulus_interval_filter([1,2,3,4], period_length = 2) == [1,3]
        assert stimulus_interval_filter([1,2,3,4], period_length = 2, offset = 1) == [2,4]      
        
    def test_get_st_from_spike_times_and_stim_times(self):
        spike_times = [5, 10, 11, 12, 20,25]
        stim_times = [10,20]
        st = get_st_from_spike_times_and_stim_times(spike_times, stim_times)
        np.testing.assert_almost_equal(st.values, I.np.array([[0,1,2], [0,5,np.NaN]]))
        assert get_st_from_spike_times_and_stim_times([],[]).to_dict() == {}
        assert get_st_from_spike_times_and_stim_times([1,2],[]).to_dict() == {0: {0: 1.0}, 1: {0: 2.0}}
        assert get_st_from_spike_times_and_stim_times([1,2],[.5]).to_dict() == {0: {0: .5}, 1: {0: 1.5}}
        
    def test_strip_st(self):
        df = pd.DataFrame({'trial1': {'0': 1, '1':2.1}, 'trial2': {'0': 1, '1':2.2}}).T
        v = df.values
        df['test'] = 'some_string'
        I.np.testing.assert_almost_equal(v, strip_st(df).values)
        
    def test_SpikeDetectionCreastTrough_spike_detection(self):
        tst = _TestSpikeTimes([0,1,2,3,4,5,6,7,8,9,10], [0,0,1,-1,0,0,1,-.5,0,0,0])
        sd = SpikeDetectionCreastTrough(tst)
        sd.run_analysis()
        assert sd.spike_times == [2.0, 6.0]
        
        tst = _TestSpikeTimes([0,1,2,3,4,5,6,7,8,9,10], [0,0,1,-1,0,0,1,-.5,0,0,0])
        sd = SpikeDetectionCreastTrough(tst, lim_trough=-.7, lim_creast=.7)
        sd.run_analysis()
        assert sd.spike_times == [2.0]
        
        tst = _TestSpikeTimes([0,1,2,3,4,5,6,7,8,9,10], [0,0,1,-2,0,0,1,-1,0,0,0])
        sd = SpikeDetectionCreastTrough(tst, lim_trough=-1., lim_creast=.7)
        sd.run_analysis()
        assert sd.spike_times == [2.0, 6.0]
        
        tst = _TestSpikeTimes([0,1,2,3,4,5,6,7,8,9,10], [0,1,1,-2,0,0,1,-1,0,0,0])
        sd = SpikeDetectionCreastTrough(tst, lim_trough=-1., lim_creast=.7)
        sd.run_analysis()
        assert sd.spike_times == [2.0, 6.0]
        
        tst = _TestSpikeTimes([0,1,2,3,4,5,6,7,8,9,10], [0,1,0,-2,0,0,1,-1,0,0,0])
        sd = SpikeDetectionCreastTrough(tst, lim_trough=-1., lim_creast=.7)
        sd.run_analysis()
        assert sd.spike_times == [1.0, 6.0]
        
        tst = _TestSpikeTimes([0,1,2,3,4,5,6,7,8,9,10], [0,1,0,0,-2,0,1,-1,0,0,0])
        sd = SpikeDetectionCreastTrough(tst, lim_trough=-1., lim_creast=.7)
        sd.run_analysis()
        assert sd.spike_times == [6.0]
        
        tst = _TestSpikeTimes([0,1,2,3,4,5,6,7,8,9,10], [0,1,0,0,-2,0,1,-1,0,0,0])
        sd = SpikeDetectionCreastTrough(tst, lim_trough=-1., lim_creast=1.1)
        sd.run_analysis()
        assert sd.spike_times == []
        
        tst = _TestSpikeTimes([0,1,2,3,4,5,6,7,8,9,10], [0,1,0,0,-2,0,1,-1,0,0,0])
        sd = SpikeDetectionCreastTrough(tst, lim_trough=-1., lim_creast=.5, max_creast_trough_interval=3)
        sd.run_analysis()
        assert sd.spike_times == [1.0, 6.0]  
        
    def test_SpikeDetectionCreastTrough_lim_detection(self):
        v = []
        t = list(range(len(v)))
        tst = _TestSpikeTimes(t,v)
        sd = SpikeDetectionCreastTrough(tst, lim_trough='minimum', lim_creast='minimum', max_creast_trough_interval=3)
        I.np.testing.assert_almost_equal(sd.lim_creast, .4)
        I.np.testing.assert_almost_equal(sd.lim_trough, -.4)
        
        v = [0,.4,0]
        t = list(range(len(v)))
        tst = _TestSpikeTimes(t,v)
        sd = SpikeDetectionCreastTrough(tst, lim_trough='minimum', lim_creast='minimum', max_creast_trough_interval=3)
        I.np.testing.assert_almost_equal(sd.lim_creast, .5)
        I.np.testing.assert_almost_equal(sd.lim_trough, -.4)
        
        v = [0,.4,-.4]
        t = list(range(len(v)))
        tst = _TestSpikeTimes(t,v)
        sd = SpikeDetectionCreastTrough(tst, lim_trough='minimum', lim_creast='minimum', max_creast_trough_interval=3)
        I.np.testing.assert_almost_equal(sd.lim_creast, .5)
        I.np.testing.assert_almost_equal(sd.lim_trough, -.4)
        
        v = [0,.4,-.4,0.]
        t = list(range(len(v)))
        tst = _TestSpikeTimes(t,v)
        sd = SpikeDetectionCreastTrough(tst, lim_trough='minimum', lim_creast='minimum', max_creast_trough_interval=3)
        I.np.testing.assert_almost_equal(sd.lim_creast, .5)
        I.np.testing.assert_almost_equal(sd.lim_trough, -.5)
        
        v = []
        t = list(range(len(v)))
        tst = _TestSpikeTimes(t,v)
        sd = SpikeDetectionCreastTrough(tst, lim_trough='zero', lim_creast='zero', max_creast_trough_interval=3)
        I.np.testing.assert_almost_equal(sd.lim_creast, .4)
        I.np.testing.assert_almost_equal(sd.lim_trough, -.4)

        v = [0,.4,-.4,0.]
        t = list(range(len(v)))
        tst = _TestSpikeTimes(t,v)
        sd = SpikeDetectionCreastTrough(tst, lim_trough='zero', lim_creast='zero', max_creast_trough_interval=3)
        I.np.testing.assert_almost_equal(sd.lim_creast, .5)
        I.np.testing.assert_almost_equal(sd.lim_trough, -.5)
    
    def test_get_period_label_by_time(self):
        periods = {'1onset': (0,100), '2sustained':(100,1000)}
        assert get_period_label_by_time(periods, 0) == '1onset'
        assert get_period_label_by_time(periods, 100) == '2sustained'
        assert get_period_label_by_time(periods, -100) == 'undefined'
        assert get_period_label_by_time(periods, 1100) == 'undefined'
        
    def test_event_analysis_ISIn(self):
        st = [-1,2,4,7,11]
        tst = _TestSpikeTimes(spike_times=st)  # init test spike times object with just the spike_times attribute
        stap = STAPlugin_ISIn()  # spike time analysis plugin
        stap.setup(SpikeTimesAnalysis(tst))
        nan = np.NaN
        expected = I.pd.DataFrame({'ISI_1': {0: 3.0, 1: 2.0, 2: 3.0, 3: 4.0, 4: nan},
         'ISI_2': {0: 5.0, 1: 5.0, 2: 7.0, 3: nan, 4: nan},
         'ISI_3': {0: 8.0, 1: 9.0, 2: nan, 3: nan, 4: nan},
         'ISI_4': {0: 12.0, 1: nan, 2: nan, 3: nan, 4: nan},
         'event_time': {0: -1, 1: 2, 2: 4, 3: 7, 4: 11}})
        pd.util.testing.assert_frame_equal(pd.DataFrame(expected), stap.event_analysis_ISIn(st))
        
    def test_event_analysis_bursts(self):
        nan = np.NaN
        spike_times = [[], [1], [1, 2], [1, 2, 3], [1, 2, 3, 4]]
        expecteds = [
            I.pd.DataFrame(dtype=float),
            I.pd.DataFrame({'event_class': {0: 'singlet'}, 'event_time': {0: 1}}),
            I.pd.DataFrame({'ISI_1': {0: 1}, 'event_class': {0: 'doublet'}, 'event_time': {0: 1}}),
            I.pd.DataFrame({'ISI_1': {0: 1},
                'ISI_2': {0: 2},
                'event_class': {0: 'triplet'},
                'event_time': {0: 1}}
                ),
            I.pd.DataFrame({'ISI_1': {0: 1.0, 1: nan},
                'ISI_2': {0: 2.0, 1: nan},
                'event_class': {0: 'triplet', 1: 'singlet'},
                'event_time': {0: 1, 1: 4}}
                )
        ]

        for st, expected in zip(spike_times, expecteds):
            tst = _TestSpikeTimes(spike_times=st)  # init test spike times object with just the spike_times attribute
            stap = STAPlugin_bursts()  # spike time analysis plugin
            stap.setup(SpikeTimesAnalysis(tst))
            df = stap.event_analysis_bursts(st, event_maxtimes=stap.event_maxtimes, event_names=stap.event_names)
            I.pd.util.testing.assert_frame_equal(expected, df, 
            check_like=True,  # ignore order of columns with check_like
            )  

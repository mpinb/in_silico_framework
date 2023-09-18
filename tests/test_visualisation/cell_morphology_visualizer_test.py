from visualize.cell_morphology_visualizer import CellMorphologyVisualizer, CellMorphologyInteractiveVisualizer
from .context import *
from single_cell_parser.serialize_cell import *
from tests import setup_current_injection_experiment
import six
import pytest
import distributed

class TestCellMorphologyVisualizer:
    def setup_class(self):
        self.client = distributed.client_object_duck_typed
        self.cell = setup_current_injection_experiment()
        self.cmv = CellMorphologyVisualizer(self.cell, align_trunk=six.PY3)  # don't align trunk in py2, ithas no scipy Rotation object
        self.t_start, self.t_end, self.t_step = self.cmv.t_start, self.cmv.t_end, (self.cmv.t_end-self.cmv.t_start)//2  # a two-frame gif
    
    @pytest.mark.skipif(six.PY2, reason="The cell_morphology_visualizer methods are not available on Py2")
    def test_init(self):
        assert isinstance(self.cmv, CellMorphologyVisualizer)

    @pytest.mark.skipif(six.PY2, reason="The cell_morphology_visualizer methods are not available on Py2")
    def test_show_morphology_3d(self):
        self.cmv.show_morphology_3d(highlight_section=1)

    @pytest.mark.skipif(six.PY2, reason="The cell_morphology_visualizer methods are not available on Py2")
    def test_show_voltage_in_morphology_3d(self):
        self.cmv.show_voltage_in_morphology_3d(time_point=0, highlight_section=1)

    @pytest.mark.skipif(six.PY2, reason="The cell_morphology_visualizer methods are not available on Py2")
    def test_show_voltage_synapses_in_morphology_3d(self):
        """
        TODO: test highlight arrow?
        """
        self.cmv.show_voltage_synapses_in_morphology_3d(time_point=0)

    @pytest.mark.skipif(six.PY2, reason="The cell_morphology_visualizer methods are not available on Py2")
    def test_write_gif_voltage_synapses_in_morphology_3d(self, tmpdir):
        outdir = str(tmpdir.dirname)
        self.cmv.write_gif_voltage_synapses_in_morphology_3d(
            images_path=outdir, out_path=os.path.join(outdir, "test_gif.gif"),
            t_start=self.t_start, t_end=self.t_end, t_step=self.t_step,
            client=distributed.client_object_duck_typed
            )

    @pytest.mark.skipif(six.PY2, reason="The cell_morphology_visualizer methods are not available on Py2")
    @pytest.mark.xfail(strict=False, reason="ffmpeg is not installed on the local runner")
    def test_write_video_voltage_synapses_in_morphology_3d(self, tmpdir):
        outdir = str(tmpdir.dirname)
        self.cmv.write_video_voltage_synapses_in_morphology_3d(
            images_path=outdir, out_path=os.path.join(outdir, "test_video.mp4"), 
            t_start=self.t_start, t_end=self.t_end, t_step=self.t_end,
            client=distributed.client_object_duck_typed
        )

    @pytest.mark.skipif(six.PY2, reason="The cell_morphology_visualizer methods are not available on Py2")
    def test_display_animation_voltage_synapses_in_morphology_3d(self, tmpdir):
        outdir = str(tmpdir.dirname)
        self.cmv.display_animation_voltage_synapses_in_morphology_3d(
            images_path=outdir, t_start=self.t_start, t_end=self.t_end, t_step=self.t_step,
            client=distributed.client_object_duck_typed
        )

class TestCellMorphologyInteractiveVisualizer:
    def setup_class(self):
        self.client = distributed.client_object_duck_typed
        self.cell = setup_current_injection_experiment(rangevars=['NaTa_t.ina'])
        self.cmiv = CellMorphologyInteractiveVisualizer(cell=self.cell, align_trunk=six.PY3, show=False)
        self.t_start, self.t_end, self.t_step = 0, 1, 1  # a two-frame test
    
    @pytest.mark.skipif(six.PY2, reason="Interactive visualizations are not available on Py2")
    def test_display_interactive_morphology_3d(self):
        self.cmiv.display_interactive_morphology_3d(
            t_start=self.t_start, t_end=self.t_end, t_step=self.t_step)

    @pytest.mark.skipif(six.PY2, reason="Interactive visualizations are not available on Py2")
    def test_display_interactive_voltage_in_morphology_3d(self):
        self.cmiv.display_interactive_voltage_in_morphology_3d(
            t_start=self.t_start, t_end=self.t_end, t_step=self.t_step)

    @pytest.mark.skipif(six.PY2, reason="Interactive visualizations are not available on Py2")
    def test_display_interactive_ion_dynamics_in_morphology_3d(self):
        self.cmiv.display_interactive_ion_dynamics_in_morphology_3d(
            ion_keyword='NaTa_t.ina',
            t_start=self.t_start, t_end=self.t_end, t_step=self.t_step)
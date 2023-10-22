from visualize.cell_morphology_visualizer import CellMorphologyVisualizer, CellMorphologyInteractiveVisualizer
from .context import *
from single_cell_parser.serialize_cell import *
from tests import setup_current_injection_experiment
import six
import pytest
import distributed


class TestCellMorphologyVisualizer:

    def setup_class(self):
        self.cell = setup_current_injection_experiment()
        self.cmv = CellMorphologyVisualizer(
            self.cell, align_trunk=six.PY3
        )  # don't align trunk in py2, ithas no scipy Rotation object
        self.cmv.t_start, self.cmv.t_end, self.cmv.t_step = 0, 1, 0.5

    @pytest.mark.skipif(
        six.PY2,
        reason="The cell_morphology_visualizer methods are not available on Py2"
    )
    def test_init(self):
        assert isinstance(self.cmv, CellMorphologyVisualizer)

    @pytest.mark.skipif(
        six.PY2,
        reason="The cell_morphology_visualizer methods are not available on Py2"
    )
    def test_show_morphology_3d(self):
        self.cmv.show_morphology_3d(highlight_section=1, plot=False)

    @pytest.mark.skipif(
        six.PY2,
        reason="The cell_morphology_visualizer methods are not available on Py2"
    )
    def test_show_voltage_in_morphology_3d(self):
        self.cmv.show_voltage_in_morphology_3d(time_point=0,
                                               highlight_section=1,
                                               plot=False)

    @pytest.mark.skipif(
        six.PY2,
        reason="The cell_morphology_visualizer methods are not available on Py2"
    )
    def test_show_voltage_synapses_in_morphology_3d(self):
        """
        TODO: test highlight arrow?
        """
        self.cmv.show_voltage_synapses_in_morphology_3d(time_point=0,
                                                        plot=False)

    @pytest.mark.skipif(
        six.PY2,
        reason="The cell_morphology_visualizer methods are not available on Py2"
    )
    def test_write_gif_voltage_synapses_in_morphology_3d(self, tmpdir, client):
        outdir = str(tmpdir.dirname)
        self.cmv.write_gif_voltage_synapses_in_morphology_3d(
            images_path=outdir,
            out_path=os.path.join(outdir, "test_gif.gif"),
            client=client)

    @pytest.mark.skipif(
        six.PY2,
        reason="The cell_morphology_visualizer methods are not available on Py2"
    )
    @pytest.mark.xfail(strict=False,
                       reason="ffmpeg is not installed on the local runner")
    def test_write_video_voltage_synapses_in_morphology_3d(
            self, tmpdir, client):
        outdir = str(tmpdir.dirname)
        self.cmv.write_video_voltage_synapses_in_morphology_3d(
            images_path=outdir,
            out_path=os.path.join(outdir, "test_video.mp4"),
            client=client)

    @pytest.mark.skipif(
        six.PY2,
        reason="The cell_morphology_visualizer methods are not available on Py2"
    )
    def test_display_animation_voltage_synapses_in_morphology_3d(
            self, tmpdir, client):
        outdir = str(tmpdir.dirname)
        self.cmv.display_animation_voltage_synapses_in_morphology_3d(
            images_path=outdir, client=client)


class TestCellMorphologyInteractiveVisualizer:

    def setup_class(self):
        self.ion_keyword = 'NaTa_t.ina'
        self.cell = setup_current_injection_experiment(
            rangevars=[self.ion_keyword])
        self.cmiv = CellMorphologyInteractiveVisualizer(cell=self.cell,
                                                        align_trunk=six.PY3,
                                                        show=False)
        self.cmiv.t_start, self.cmiv.t_end, self.cmiv.t_step = 0, 1, 0.5  # a two-frame test

    @pytest.mark.skipif(
        six.PY2, reason="Interactive visualizations are not available on Py2")
    def test_has_ion_data(self):
        self.cmiv._calc_ion_dynamics_timeseries(ion_keyword=self.ion_keyword)
        assert self.ion_keyword in self.cmiv.scalar_data.keys()
        # ionic data at timepoint 0
        # should be one value per line connecting all te points in the morphology
        # n_lines = n_points + n_section_connections = n_points + n_sections - 1
        assert len(self.cmiv.scalar_data[self.ion_keyword][0]) == len(
            self.cmiv.morphology) + self.cmiv.n_sections - 1

    @pytest.mark.skipif(
        six.PY2, reason="Interactive visualizations are not available on Py2")
    def test_display_interactive_morphology_3d(self):
        fig = self.cmiv.display_interactive_morphology_3d()

    @pytest.mark.skipif(
        six.PY2, reason="Interactive visualizations are not available on Py2")
    def test_display_interactive_voltage_in_morphology_3d(self):
        fig = self.cmiv.display_interactive_voltage_in_morphology_3d()

    @pytest.mark.skipif(
        six.PY2, reason="Interactive visualizations are not available on Py2")
    def test_display_interactive_ion_dynamics_in_morphology_3d(self):
        fig = self.cmiv.display_interactive_ion_dynamics_in_morphology_3d(
            ion_keyword='NaTa_t.ina')

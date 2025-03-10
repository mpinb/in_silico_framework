from visualize.cell_morphology_visualizer import CellMorphologyVisualizer, CellMorphologyInteractiveVisualizer
from .context import *
from single_cell_parser.serialize_cell import *
from tests import setup_synapse_activation_experiment
import six
import pytest
import distributed


class TestCellMorphologyVisualizer:
    def setup_class(self):
        self.cell = setup_synapse_activation_experiment()
        self.cmv = CellMorphologyVisualizer(
            self.cell, 
            align_trunk=six.PY3,
            t_start=0, t_stop=1,t_step=0.5
        )  # don't align trunk in py2, scipy in Py2.7 has no Rotation object

    @pytest.mark.skipif(
        six.PY2,
        reason="The cell_morphology_visualizer methods are not available on Py2")
    def test_init(self):
        assert isinstance(self.cmv, CellMorphologyVisualizer)

    @pytest.mark.skipif(
        six.PY2,
        reason="The cell_morphology_visualizer methods are not available on Py2")
    def test_plot_morphology(self):
        self.cmv.plot()
        
    def test_highlight_section(self):
        self.cmv.plot(highlight_section=1)

    @pytest.mark.skipif(
        six.PY2,
        reason="The cell_morphology_visualizer methods are not available on Py2")
    def test_plot_voltage(self):
        self.cmv.plot(
            color="voltage",
            show_legend=True,
            time_point=0)

    @pytest.mark.skipif(
        six.PY2,
        reason="The cell_morphology_visualizer methods are not available on Py2")
    def test_plot_synapses(self):
        self.cmv.plot(
            color="voltage",
            show_synapses=True,
            time_point=0)

    @pytest.mark.skipif(
        six.PY2,
        reason="The cell_morphology_visualizer methods are not available on Py2")
    def test_write_gif(self, tmpdir, client):
        outdir = str(tmpdir.dirname)
        self.cmv.write_gif(
            images_path=outdir,
            color="voltage",
            show_synapses=True,
            out_name=os.path.join(outdir, "test_gif.gif"),
            client=client)

    @pytest.mark.skipif(
        six.PY2,
        reason="The cell_morphology_visualizer methods are not available on Py2")
    @pytest.mark.xfail(strict=False,
                       reason="ffmpeg is not installed on the local runner")
    def test_write_video(
            self, tmpdir, client):
        outdir = str(tmpdir.dirname)
        self.cmv.write_video(
            images_path=outdir,
            out_path=os.path.join(outdir, "test_video.mp4"),
            client=client)

    @pytest.mark.skipif(
        six.PY2,
        reason="The cell_morphology_visualizer methods are not available on Py2")
    def test_animation(
            self, tmpdir, client):
        outdir = str(tmpdir.dirname)
        self.cmv.animation(
            color="voltage",
            show_synapses=True,
            show_legend=True,
            images_path=outdir, 
            client=client)


class TestCellMorphologyInteractiveVisualizer:
    def setup_class(self):
        self.ion_keyword = 'NaTa_t.ina'
        self.cell = setup_synapse_activation_experiment(
            rangevars=[self.ion_keyword])
        self.cmiv = CellMorphologyInteractiveVisualizer(
            cell=self.cell,
            t_start=0, t_stop=1, t_step=0.5,
            align_trunk=six.PY3,
            show=False)
        self.cmiv.show = False

    @pytest.mark.skipif(
        six.PY2, reason="Interactive visualizations are not available on Py2")
    def test_has_ion_data(self):
        self.cmiv._calc_ion_dynamics_timeseries(ion_keyword=self.ion_keyword)
        assert self.ion_keyword in self.cmiv.ion_dynamics_timeseries.keys()
        # ionic data at timepoint 0
        # should be one value per line connecting all te points in the morphology
        # n_lines = n_points + n_section_connections = n_points + n_sections - 1
        assert len(self.cmiv.ion_dynamics_timeseries[self.ion_keyword][0]
            ) == self.cmiv.n_sections

    @pytest.mark.skipif(
        six.PY2, reason="Interactive visualizations are not available on Py2")
    def test_display_interactive_morphology_3d(self):
        fig = self.cmiv.interactive_plot()

    @pytest.mark.skipif(
        six.PY2, reason="Interactive visualizations are not available on Py2")
    def test_display_interactive_voltage(self):
        fig = self.cmiv.interactive_plot(color="voltage", time_point=0)

    @pytest.mark.skipif(
        six.PY2, reason="Interactive visualizations are not available on Py2")
    def test_display_interactive_ion_dynamics(self):
        fig = self.cmiv.interactive_plot(color='NaTa_t.ina', time_point=0)

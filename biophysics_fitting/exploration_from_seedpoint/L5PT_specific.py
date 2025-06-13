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
Hardcoded values for parameter names and objectives for a Layer 5 pyramidal tract neuron in the rat barrel cortex.
can be used as a template for other cells.

:skip-doc:
"""

PARAM_NAMES = ['ephys.CaDynamics_E2_v2.apic.decay', 'ephys.CaDynamics_E2_v2.apic.gamma', 'ephys.CaDynamics_E2_v2.axon.decay', 'ephys.CaDynamics_E2_v2.axon.gamma', \
'ephys.CaDynamics_E2_v2.soma.decay', 'ephys.CaDynamics_E2_v2.soma.gamma', 'ephys.Ca_HVA.apic.gCa_HVAbar', 'ephys.Ca_HVA.axon.gCa_HVAbar', 'ephys.Ca_HVA.soma.gCa_HVAbar', \
'ephys.Ca_LVAst.apic.gCa_LVAstbar', 'ephys.Ca_LVAst.axon.gCa_LVAstbar', 'ephys.Ca_LVAst.soma.gCa_LVAstbar', 'ephys.Im.apic.gImbar', 'ephys.K_Pst.axon.gK_Pstbar', \
'ephys.K_Pst.soma.gK_Pstbar', 'ephys.K_Tst.axon.gK_Tstbar', 'ephys.K_Tst.soma.gK_Tstbar', 'ephys.NaTa_t.apic.gNaTa_tbar', 'ephys.NaTa_t.axon.gNaTa_tbar', \
'ephys.NaTa_t.soma.gNaTa_tbar', 'ephys.Nap_Et2.axon.gNap_Et2bar', 'ephys.Nap_Et2.soma.gNap_Et2bar', 'ephys.SK_E2.apic.gSK_E2bar', 'ephys.SK_E2.axon.gSK_E2bar', \
'ephys.SK_E2.soma.gSK_E2bar', 'ephys.SKv3_1.apic.gSKv3_1bar', 'ephys.SKv3_1.apic.offset', 'ephys.SKv3_1.apic.slope', 'ephys.SKv3_1.axon.gSKv3_1bar', 'ephys.SKv3_1.soma.gSKv3_1bar', \
'ephys.none.apic.g_pas', 'ephys.none.axon.g_pas', 'ephys.none.dend.g_pas', 'ephys.none.soma.g_pas', 'scale_apical.scale']


# from biphysics_fitting.hay_evaluation
objectives_step = [
    'AI1','AI2','AI3','APh1','APh2','APh3','APw1','APw2','APw3','DI1','DI2',
    'ISIcv1','ISIcv2','ISIcv3','TTFS1','TTFS2','TTFS3','fAHPd1','fAHPd2','fAHPd3',
    'mf1','mf2','mf3','sAHPd1','sAHPd2','sAHPd3','sAHPt1','sAHPt2','sAHPt3'
    ]

objectives_BAC = [
    'BAC_APheight', 'BAC_ISI', 'BAC_ahpdepth', 'BAC_caSpike_height', 'BAC_caSpike_width', 
    'BAC_spikecount', 'bAP_APheight', 'bAP_APwidth', 'bAP_att2', 'bAP_att3', 'bAP_spikecount'
    ]

objectives_2BAC = [
    '1BAC_APheight', '1BAC_ISI', '1BAC_ahpdepth', '1BAC_caSpike_height', '1BAC_caSpike_width', 
    '1BAC_spikecount', '2BAC_APheight', '2BAC_ISI', '2BAC_ahpdepth', '2BAC_caSpike_height', 
    '2BAC_caSpike_width', '2BAC_spikecount', 'bAP_APheight', 'bAP_APwidth', 'bAP_att2', 
    'bAP_att3', 'bAP_spikecount'
    ]
#########################################
# naming converters scp <--> hay
#########################################
import six


def hay_param_to_scp_neuron_param(p):
    p = p.split('.')
    if p[1] == 'axon':
        p[1] = 'AIS'
    elif p[1] == 'apic':
        p[1] = 'ApicalDendrite'
    elif p[1] == 'dend':
        p[1] = 'Dendrite'
    elif p[1] == 'soma':
        p[1] = 'Soma'
    if p[0] == 'none' and p[2] == 'g_pas':
        p[0] = 'pas'
        p[2] = 'g'
    return '.'.join([p[1], 'mechanisms', 'range', p[0], p[2]])


def hay_params_to_scp_neuron_params(params):
    return [hay_param_to_scp_neuron_param(p) for p in params]


#############################################
# template and template modify functions
#############################################


def get_L5tt_template():
    p = {
        'NMODL_mechanisms': {
            'channels': '/'
        },
        'info': {
            'author': 'regger and abast',
            'date': '2018',
            'name': 'scp_optimizer'
        },
        'mech_globals': {},
        'neuron': {
            'AIS': {
                'mechanisms': {
                    'global': {},
                    'range': {
                        'CaDynamics_E2': {
                            'decay': None,
                            'gamma': None,
                            'spatial': 'uniform'
                        },
                        'Ca_HVA': {
                            'gCa_HVAbar': None,
                            'spatial': 'uniform'
                        },
                        'Ca_LVAst': {
                            'gCa_LVAstbar': None,
                            'spatial': 'uniform'
                        },
                        'Ih': {
                            'gIhbar': 8e-05,
                            'spatial': 'uniform'
                        },
                        'K_Pst': {
                            'gK_Pstbar': None,
                            'spatial': 'uniform'
                        },
                        'K_Tst': {
                            'gK_Tstbar': None,
                            'spatial': 'uniform'
                        },
                        'NaTa_t': {
                            'gNaTa_tbar': None,
                            'spatial': 'uniform'
                        },
                        'Nap_Et2': {
                            'gNap_Et2bar': None,
                            'spatial': 'uniform'
                        },
                        'SK_E2': {
                            'gSK_E2bar': None,
                            'spatial': 'uniform'
                        },
                        'SKv3_1': {
                            'gSKv3_1bar': None,
                            'spatial': 'uniform'
                        },
                        'pas': {
                            'e': -90,
                            'g': None,
                            'spatial': 'uniform'
                        }
                    }
                },
                'properties': {
                    'Ra': 100.0,
                    'cm': 1.0,
                    'ions': {
                        'ek': -85.0,
                        'ena': 50.0
                    }
                }
            },
            'ApicalDendrite': {
                'mechanisms': {
                    'global': {},
                    'range': {
                        'CaDynamics_E2': {
                            'decay': None,
                            'gamma': None,
                            'spatial': 'uniform'
                        },
                        'Ca_HVA': {
                            'begin': 900.0,
                            'end': 1100.0,
                            'gCa_HVAbar': None,
                            'outsidescale': 0.1,
                            'spatial': 'uniform_range'
                        },
                        'Ca_LVAst': {
                            'begin': 900.0,
                            'end': 1100.0,
                            'gCa_LVAstbar': None,
                            'outsidescale': 0.01,
                            'spatial': 'uniform_range'
                        },
                        'Ih': {
                            '_lambda': 3.6161,
                            'distance': 'relative',
                            'gIhbar': 0.0002,
                            'linScale': 2.087,
                            'offset': -0.8696,
                            'spatial': 'exponential',
                            'xOffset': 0.0
                        },
                        'Im': {
                            'gImbar': None,
                            'spatial': 'uniform'
                        },
                        'NaTa_t': {
                            'gNaTa_tbar': None,
                            'spatial': 'uniform'
                        },
                        'SK_E2': {
                            'gSK_E2bar': None,
                            'spatial': 'uniform'
                        },
                        'SKv3_1': {
                            'gSKv3_1bar': None,
                            'spatial': 'uniform'
                        },
                        'pas': {
                            'e': -90,
                            'g': None,
                            'spatial': 'uniform'
                        }
                    }
                },
                'properties': {
                    'Ra': 100.0,
                    'cm': 2.0,
                    'ions': {
                        'ek': -85.0,
                        'ena': 50.0
                    }
                }
            },
            'Dendrite': {
                'mechanisms': {
                    'global': {},
                    'range': {
                        'Ih': {
                            'gIhbar': 0.0002,
                            'spatial': 'uniform'
                        },
                        'pas': {
                            'e': -90.0,
                            'g': None,
                            'spatial': 'uniform'
                        }
                    }
                },
                'properties': {
                    'Ra': 100.0,
                    'cm': 2.0
                }
            },
            'Myelin': {
                'mechanisms': {
                    'global': {},
                    'range': {
                        'pas': {
                            'e': -90.0,
                            'g': 4e-05,
                            'spatial': 'uniform'
                        }
                    }
                },
                'properties': {
                    'Ra': 100.0,
                    'cm': 0.02
                }
            },
            'Soma': {
                'mechanisms': {
                    'global': {},
                    'range': {
                        'CaDynamics_E2': {
                            'decay': None,
                            'gamma': None,
                            'spatial': 'uniform'
                        },
                        'Ca_HVA': {
                            'gCa_HVAbar': None,
                            'spatial': 'uniform'
                        },
                        'Ca_LVAst': {
                            'gCa_LVAstbar': None,
                            'spatial': 'uniform'
                        },
                        'Ih': {
                            'gIhbar': 8e-05,
                            'spatial': 'uniform'
                        },
                        'K_Pst': {
                            'gK_Pstbar': None,
                            'spatial': 'uniform'
                        },
                        'K_Tst': {
                            'gK_Tstbar': None,
                            'spatial': 'uniform'
                        },
                        'NaTa_t': {
                            'gNaTa_tbar': None,
                            'spatial': 'uniform'
                        },
                        'Nap_Et2': {
                            'gNap_Et2bar': None,
                            'spatial': 'uniform'
                        },
                        'SK_E2': {
                            'gSK_E2bar': None,
                            'spatial': 'uniform'
                        },
                        'SKv3_1': {
                            'gSKv3_1bar': None,
                            'spatial': 'uniform'
                        },
                        'pas': {
                            'e': -90,
                            'g': None,
                            'spatial': 'uniform'
                        }
                    }
                },
                'properties': {
                    'Ra': 100.0,
                    'cm': 1.0,
                    'ions': {
                        'ek': -85.0,
                        'ena': 50.0
                    }
                }
            },
            'filename': None
        },
        'sim': {
            'T': 34.0,
            'Vinit': -75.0,
            'dt': 0.025,
            'recordingSites': [],
            'tStart': 0.0,
            'tStop': 300.0
        }
    }
    from sumatra.parameters import NTParameterSet
    return NTParameterSet(p['neuron'])


def set_morphology(cell_param, filename=None):
    cell_param.filename = filename
    return cell_param


def set_ephys(cell_param, params=None):
    'updates cell_param file. parameter names reflect the hay naming convention.'
    for k, v in six.iteritems(params):
        cell_param[hay_param_to_scp_neuron_param(k)] = float(v)
    return cell_param


def set_param(cell_param, params=None):
    'updates cell_param file. parameter names reflect the hierarchy in the cell_param file itself.'
    for k, v in six.iteritems(params):
        p = cell_param
        for kk in k.split('.')[:-1]:
            p = p[kk]
        p[k.split('.')[-1]] = v
    return cell_param


def set_many_param(cell_param, params=None):

    master_values = {}

    for k, v in six.iteritems(params):
        if '.' not in k:
            master_values[k] = v

    for k, v in six.iteritems(params):
        if '.' in k:
            stored_value = master_values[k.split('.')[0]]
            p = cell_param
            for key in k.split('.')[1:-1]:
                p = p[key]
            p[k.split('.')[-1]] = stored_value

    return cell_param


def set_hot_zone(cell_param, min_=None, max_=None, outsidescale_sections=None):
    cell_param['ApicalDendrite'].mechanisms.range['Ca_LVAst']['begin'] = min_
    cell_param['ApicalDendrite'].mechanisms.range['Ca_LVAst']['end'] = max_
    cell_param['ApicalDendrite'].mechanisms.range['Ca_HVA']['begin'] = min_
    cell_param['ApicalDendrite'].mechanisms.range['Ca_HVA']['end'] = max_
    if outsidescale_sections is not None:
        assert isinstance(outsidescale_sections, list)
        cell_param['ApicalDendrite'].mechanisms.range['Ca_LVAst'][
            'outsidescale_sections'] = outsidescale_sections
        cell_param['ApicalDendrite'].mechanisms.range['Ca_HVA'][
            'outsidescale_sections'] = outsidescale_sections
    return cell_param

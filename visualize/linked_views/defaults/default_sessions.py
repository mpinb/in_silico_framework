def biophysics_fitting_vaex_1():
    return {
        "data": {
            "grammar": {
                "views": [{
                    "configuration": {
                        "density_grid_shape": [100, 100],
                        "format": "count",
                        "pointOpacity": 0.8,
                        "pointSize": 5
                    },
                    "dataColumn": ["PCA-ephys-1", "PCA-ephys-2"],
                    "id": 1,
                    "maxNumDatasources": 2,
                    "minNumDatasources": 2,
                    "name": "2-channel",
                    "dataTable": "Abstract DataFrame",
                    "type": "density-2-channel"
                }, {
                    "configuration": {
                        "density_grid_shape": [100, 100],
                        "format": "median",
                        "pointOpacity": 0.8,
                        "pointSize": 5
                    },
                    "dataColumn": [
                        "ephys.CaDynamics_E2_v2.axon.decay",
                        "ephys.CaDynamics_E2_v2.axon.gamma",
                        "ephys.SKv3_1.axon.gSKv3_1bar"
                    ],
                    "id": 2,
                    "maxNumDatasources": 3,
                    "minNumDatasources": 3,
                    "name": "3-channel",
                    "dataTable": "Abstract DataFrame",
                    "type": "density-3-channel"
                }],
                "grid": {
                    "cols": 12,
                    "rowHeight": 100,
                    "width": 1200
                },
                "initialLayout": "L1",
                "interactions": {},
                "layouts": {
                    "L1": [{
                        "h": 6,
                        "view": "3-channel",
                        "w": 12,
                        "x": 0,
                        "y": 0
                    }]
                }
            }
        }
    }


def biophysics_fitting_vaex_2():
    return {
        "data": {
            "grammar": {
                "views": [{
                    "configuration": {
                        "density_grid_shape": [100, 100],
                        "format": "count",
                        "pointOpacity": 0.8,
                        "pointSize": 5
                    },
                    "dataColumn": [
                        "ephys.Ca_HVA.apic.gCa_HVAbar", "ephys.K_Tst.axon.gK_Tstbar"
                    ],
                    "id": 1,
                    "maxNumDatasources": 2,
                    "minNumDatasources": 2,
                    "name": "2-channel",
                    "dataTable": "Abstract DataFrame",
                    "type": "density-2-channel"
                }, {
                    "configuration": {
                        "density_grid_shape": [100, 100],
                        "format": "median",
                        "pointOpacity": 0.8,
                        "pointSize": 5
                    },
                    "dataColumn": [
                        "ephys.CaDynamics_E2_v2.axon.decay",
                        "ephys.CaDynamics_E2_v2.axon.gamma",
                        "ephys.SKv3_1.axon.gSKv3_1bar"
                    ],
                    "id": 2,
                    "maxNumDatasources": 3,
                    "minNumDatasources": 3,
                    "name": "3-channel",
                    "dataTable": "Abstract DataFrame",
                    "type": "density-3-channel"
                }],
                "grid": {
                    "cols": 12,
                    "rowHeight": 100,
                    "width": 1200
                },
                "initialLayout": "L1",
                "interactions": {},
                "layouts": {
                    "L1": [{
                        "h": 6,
                        "view": "2-channel",
                        "w": 6,
                        "x": 0,
                        "y": 0
                    }, {
                        "h": 6,
                        "view": "3-channel",
                        "w": 6,
                        "x": 6,
                        "y": 0
                    }]
                }
            }
        }
    }

def biophysics_fitting_pandas():
    return {
        "data": {
            "grammar": {
                "grid": {
                    "cols": 18,
                    "rowHeight": 80,
                    "width": 1900
                },
                "initialLayout": "L1",
                "interactions": {
                    "charges-parcoord": [
                        {
                            "action": {
                                "assignSelection": [
                                    "charges-parcoord",
                                    "umap channel expression",
                                    "umap channel utilization",
                                    "energy efficiency vs. Ca_HVA expression"
                                ]
                            }
                        }
                    ],
                    "energy efficiency vs. Ca_HVA expression": [                        
                        {
                            "action": {
                                "intersectSelection": [
                                    "umap channel utilization",
                                    "umap channel expression",
                                    "parcoords",
                                    "PCA 1"
                                ]
                            },
                            "filter": {
                                "currentLayout": "L1"
                            }
                        }
                    ],
                    "umap channel expression": [
                        {
                            "action": {
                                "intersectSelection": [
                                    "charges-parcoord",
                                    "umap channel expression",
                                    "umap channel utilization",
                                    "energy efficiency vs. Ca_HVA expression"
                                ]
                            }
                        }
                    ],
                    "umap channel utilization": [
                        {
                            "action": {
                                "intersectSelection": [
                                    "charges-parcoord",
                                    "umap channel expression",
                                    "umap channel utilization",
                                    "energy efficiency vs. Ca_HVA expression"
                                ]
                            }
                        }
                    ]
                },
                "layouts": {
                    "L1": [
                        {
                            "h": 5,
                            "view": "umap channel expression",
                            "w": 5,
                            "x": 0,
                            "y": 0
                        },
                        {
                            "h": 5,
                            "view": "umap channel utilization",
                            "w": 5,
                            "x": 5,
                            "y": 0
                        },
                        {
                            "h": 5,
                            "view": "energy efficiency vs. Ca_HVA expression",
                            "w": 5,
                            "x": 10,
                            "y": 0
                        },
                        {
                            "h": 3,
                            "view": "charges-parcoord",
                            "w": 18,
                            "x": 0,
                            "y": 5
                        }
                    ]
                },
                "views": [
                    {
                        "dataColumn": [
                            "BAC_bifurcation_charges.Ca_HVA.ica",
                            "BAC_dist_charge",
                            "constants_bifurcation.SKv3_1.gSKv3_1bar"
                        ],
                        "dataTable": "Abstract DataFrame",
                        "id": 2,
                        "maxNumDatasources": 3,
                        "minNumDatasources": 2,
                        "name": "energy efficiency vs. Ca_HVA expression",
                        "type": "regl-scatterplot"
                    },
                    {
                        "dataColumn": [
                            "BAC_bifurcation_charges.Ca_LVAst.ica",
                            "BAC_bifurcation_charges.SK_E2.ik",
                            "BAC_bifurcation_charges.Im.ik",
                            "BAC_bifurcation_charges.SKv3_1.ik",
                            "BAC_bifurcation_charges.NaTa_t.ina",
                            "BAC_bifurcation_charges.Ca_HVA.ica",
                            "BAC_bifurcation_charges.Ih.ihcn",
                            "BAC_dist_charge"
                        ],
                        "dataTable": "Abstract DataFrame",
                        "id": 4,
                        "maxNumDatasources": 30,
                        "minNumDatasources": 2,
                        "name": "charges-parcoord",
                        "type": "plotly-parallelcoords"
                    },
                    {
                        "dataColumn": [
                            "umap_charges_x",
                            "umap_charges_y",
                            "BAC_dist_charge"
                        ],
                        "dataTable": "Abstract DataFrame",
                        "id": 5,
                        "maxNumDatasources": 3,
                        "minNumDatasources": 2,
                        "name": "umap channel utilization",
                        "type": "regl-scatterplot"
                    },
                    {
                        "dataColumn": [
                            "umap_params_x",
                            "umap_params_y",
                            "BAC_dist_charge"
                        ],
                        "dataTable": "Abstract DataFrame",
                        "id": 6,
                        "maxNumDatasources": 3,
                        "minNumDatasources": 2,
                        "name": "umap channel expression",
                        "type": "regl-scatterplot"
                    }
                ]
            }
        }
    }

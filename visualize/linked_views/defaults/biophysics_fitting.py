def workspace_1():
    return {
        "data": {
            "viewSpec": [{
                "configuration": {
                    "density_grid_shape": [100, 100],
                    "format": "count",
                    "point_opacity": 0.8,
                    "point_size": 5
                },
                "data_sources": ["PCA-ephys-1", "PCA-ephys-2"],
                "id": 1,
                "max_num_datasources": 2,
                "min_num_datasources": 2,
                "name": "2-channel",
                "table": "vaex_df",
                "type": "density-2-channel"
            }, {
                "configuration": {
                    "density_grid_shape": [100, 100],
                    "format": "median",
                    "point_opacity": 0.8,
                    "point_size": 5
                },
                "data_sources": [
                    "ephys.CaDynamics_E2_v2.axon.decay",
                    "ephys.CaDynamics_E2_v2.axon.gamma",
                    "ephys.SKv3_1.axon.gSKv3_1bar"
                ],
                "id": 2,
                "max_num_datasources": 3,
                "min_num_datasources": 3,
                "name": "3-channel",
                "table": "vaex_df",
                "type": "density-3-channel"
            }],
            "grammar": {
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


def workspace_2():
    return {
        "data": {
            "grammar": {
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
            },
            "viewSpec": [{
                "configuration": {
                    "density_grid_shape": [100, 100],
                    "format": "count",
                    "point_opacity": 0.8,
                    "point_size": 5
                },
                "data_sources": [
                    "ephys.Ca_HVA.apic.gCa_HVAbar", "ephys.K_Tst.axon.gK_Tstbar"
                ],
                "id": 1,
                "max_num_datasources": 2,
                "min_num_datasources": 2,
                "name": "2-channel",
                "table": "vaex_df",
                "type": "density-2-channel"
            }, {
                "configuration": {
                    "density_grid_shape": [100, 100],
                    "format": "median",
                    "point_opacity": 0.8,
                    "point_size": 5
                },
                "data_sources": [
                    "ephys.CaDynamics_E2_v2.axon.decay",
                    "ephys.CaDynamics_E2_v2.axon.gamma",
                    "ephys.SKv3_1.axon.gSKv3_1bar"
                ],
                "id": 2,
                "max_num_datasources": 3,
                "min_num_datasources": 3,
                "name": "3-channel",
                "table": "vaex_df",
                "type": "density-3-channel"
            }]
        }
    }

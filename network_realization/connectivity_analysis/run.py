import sys
import os

import util


def assertCommand(exitCode):
    if(exitCode != 0):
        raise RuntimeError("Execution failed")
    

if __name__ == "__main__":     
    dataFolder = "model_data"   
    numWorkers = 10

    evalFolder = os.path.join(dataFolder, "eval")
    util.makeCleanDir(evalFolder)
        
    # compute structural features using 50-50-50 grid
    for synapticSide in ["pre", "post"]:        
        assertCommand(os.system("python calc_features_mp.py {} {} 50-50-50 all {}".format(dataFolder, synapticSide, numWorkers)))     
        for bounds in ["model-volume", "C2-volume"]:
            os.symlink("subcellular_features_{}synaptic_50-50-50_all".format(synapticSide), os.path.join(dataFolder, "subcellular_features_{}synaptic_50-50-50_{}".format(synapticSide, bounds)))            
    assertCommand(os.system("python agg_pst_mp.py {} 50-50-50 all {}".format(dataFolder, numWorkers)))        
    os.symlink("cube_index_post_50-50-50_all", os.path.join(dataFolder, "cube_index_post_50-50-50_C2-volume"))
    
    # compute dense structural overlap (DSO or DSC)
    assertCommand(os.system("python calc_DSC_mp.py {} 50-50-50 C2-volume {}".format(dataFolder, numWorkers)))
    assertCommand(os.system("python calc_DSC_mp.py {} 50-50-50 all {}".format(dataFolder, numWorkers)))      

    # render connectivity matrix (downsampled)
    for mode in ["C2", "complete"]:
        assertCommand(os.system("python eval_matrix.py {} {} {}".format(dataFolder, mode, numWorkers)))
    
    # compute pairwise connection probabilities between selected neuron populations
    for mode in ["filter-ids", "compute-connectivity", "compute-stats"]:
        assertCommand(os.system("python eval_cellular.py {} {} {}".format(dataFolder, mode, numWorkers)))    

    # compute triplet motif over-/underrepresentations for different neuron populations in barrel cortex
    for mode in ["celltype-combinations", "celltype-layer-combinations", "all-column-combinations", "selected-column-cobinations", "intersomatic-distance-combinations"]:
        assertCommand(os.system("python eval_motifs.py {} {} {} sample-ids".format(dataFolder, mode, numWorkers)))    

    # compute triplet motif over-/underrepresentations using structural constraints from saturated reconstruction
    # of human temporal cortex H01 (data courtesy: Shapson-Coe et al., 2021)
    dataFolder_h01 = os.path.join(dataFolder, "structural_data_h01")
    for mode in ["h01-layer-combinations", "h01-pyramidal-combinations"]:
        assertCommand(os.system("python eval_motifs.py {} {} {}".format(dataFolder_h01, mode, numWorkers)))

    # compute structural features using 100-100-50 grid
    for synapticSide in ["pre", "post"]:                
        #assertCommand(os.system("python calc_features_mp.py {} {} 100-100-50 all {}".format(dataFolder, synapticSide, numWorkers)))    
        for bounds in ["model-volume", "C2-volume", "L4-volume"]:
            os.symlink("subcellular_features_{}synaptic_100-100-50_all".format(synapticSide), os.path.join(dataFolder, "subcellular_features_{}synaptic_100-100-50_{}".format(synapticSide, bounds)))    
    assertCommand(os.system("python agg_pst_mp.py {} 100-100-50 model-volume {}".format(dataFolder, numWorkers)))            
    
    # compute subcellular composition
    assertCommand(os.system("python eval_composition.py {} length 50-50-50 {}".format(dataFolder, numWorkers)))    
    assertCommand(os.system("python eval_composition.py {} cube-stats-ref-volume 100-100-50 {}".format(dataFolder, numWorkers)))    

    # compute structural features using different grid sizes in selected subvolume (ref-volume)
    for gridSize in ["100-100-100", "50-50-50", "25-25-25", "10-10-10", "5-5-5", "1-1-1"]:
        for synapticSide in ["pre", "post"]:
            assertCommand(os.system("python calc_features_mp.py {} {} {} ref-volume {}".format(dataFolder, synapticSide, gridSize, numWorkers)))    

    # compute relation of branch pairs to synapses for different grid sizes
    assertCommand(os.system("python eval_branch_pairs_synapses.py {} aggregate {}".format(dataFolder, numWorkers)))    
    
    # compute connections per cell pair in relation to mutual overlap
    assertCommand(os.system("python eval_connections_overlap.py {} aggregate {}".format(dataFolder, numWorkers)))
    
    # compute synapses per branch/cell pair in subvolumes
    assertCommand(os.system("python agg_pre_mp.py {} 50-50-50 ref-volume cube-index {}".format(dataFolder, numWorkers)))
    os.symlink("cube_index_post_50-50-50_all", os.path.join(dataFolder, "cube_index_post_50-50-50_ref-volume"))
    assertCommand(os.system("python eval_cluster.py {} aggregate 50-50-50 {}".format(dataFolder, numWorkers)))
    assertCommand(os.system("python eval_cluster.py {} compute 50-50-50 {}".format(dataFolder, numWorkers)))               
       
    # compute number of connected cell pairs in relation to overlapping cell pairs for different grid sizes
    for gridSize in ["100-100-100", "50-50-50", "25-25-25", "10-10-10", "5-5-5", "1-1-1"]:
        assertCommand(os.system("python eval_overlapping_connected.py {} aggregate {} {}".format(dataFolder, gridSize, numWorkers)))
    
    # retrieve detailed connectivity information and morphologies for selected cells
    for neuronId in constants.getSelectedCellIds():
        for mode in ["innervating-soma", "innervating-dsc", "dendrite-morphology", "axon-morphology"]:
            assertCommand(os.system("python eval_representative_cell.py {} {} {} {}".format(dataFolder, mode, neuronId, numWorkers)))        
    
    # compute morphological variability (effect of sample size of unique morphologies used to populate model)
    for mode in ["pre", "post"]:
        assertCommand(os.system("python eval_variability.py {} {} {}".format(dataFolder, mode, numWorkers)))

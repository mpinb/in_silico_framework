import os
import glob
import collections
import util_feature_IO


files = glob.glob("*_DSC.csv")

for file in files:
    DSC = util_feature_IO.load_DSC(file)
    agg_DSC = collections.OrderedDict()
    for postId, subvolumes in DSC.items():
        agg_DSC[postId] = {
            "soma": 0,
            "apical": 0,
            "basal": 0
        }
        for values in subvolumes.values():
            agg_DSC[postId]["soma"] += values["soma"]
            agg_DSC[postId]["apical"] += values["apical"]
            agg_DSC[postId]["basal"] += values["basal"]
    head, tail = os.path.split(file)
    outfile = "{}_agg_DSC.csv".format(tail.split("_")[0])
    util_feature_IO.write_agg_DSC(outfile, agg_DSC)

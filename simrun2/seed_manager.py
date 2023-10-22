import numpy as np
#path = '/nas1/Data_arco/used_seeds'
import os

path = os.path.join(os.path.dirname(__file__), 'used_seeds')


def get_seed(recursion_depth=0):
    '''makes sure, that every random simulation can be initiated with a new seed'''

    used_seeds = []
    try:
        used_seeds = np.fromfile('/home/abast/used_seeds', dtype='int')
        used_seeds = used_seeds.tolist()
    except IOError:
        pass

    used_seeds.extend(list(range(10000)))

    seed = np.random.randint(4294967295)  #Seed must be between 0 and 4294967295
    return seed
    if not seed in used_seeds:
        used_seeds.append(seed)
        used_seeds = np.array(used_seeds)
        used_seeds = np.unique(
            used_seeds
        )  #because otherwise, the extend command above will allways add the same seeds
        used_seeds.tofile(path)
        return seed
    elif recursion_depth >= 50:
        raise RuntimeError("Failed generating random seed")
    else:
        return get_seed(recursion_depth=recursion_depth + 1)

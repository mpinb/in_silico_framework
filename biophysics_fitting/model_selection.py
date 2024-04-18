import pandas as pd
from collections import defaultdict
from .hay_evaluation import objectives_BAC, objectives_step
from data_base.utils import convertible_to_int


def get_model_pdf_from_db(db):

    def augment_pdf(pdf, i, j):
        pdf['model_id'] = '_'.join([db.get_id(), str(i), str(j)])
        pdf['model_id'] = pdf['model_id'] + '_' + pd.Series(
            pdf.index).astype('str')
        return pdf.set_index('model_id')

    out = defaultdict(lambda: [])
    indices = [
        int(x) for x in list(db.keys()) if convertible_to_int(x)
    ]
    for i in indices:
        if not str(i) in list(db.keys()):
            continue
        max_j = max([
            int(x)
            for x in list(db[str(i)].keys())
            if convertible_to_int(x)
        ])
        if max_j == 0:  # all databases contain key '0', which is however empty. If that is the only key: skip
            continue
        for j in range(1, max_j + 1):
            out[i].append(augment_pdf(db[str(i)][str(j)], i, j))
        out[i] = pd.concat(out[i])
    return out, pd.concat(list(out.values()))


def get_pdf_selected(pdf,
                     BAC_limit=3.5,
                     step_limit=4.5,
                     objectives_BAC=objectives_BAC,
                     objectives_step=objectives_step):

    objectives = objectives_BAC + objectives_step
    pdf['sort_column'] = pdf[objectives].max(axis=1)
    p = pdf[(pdf[objectives_step].max(axis=1) < step_limit) &
            (pdf[objectives_BAC].max(
                axis=1) < BAC_limit)].sort_values('sort_column').head()
    return p, str(p.index[0])

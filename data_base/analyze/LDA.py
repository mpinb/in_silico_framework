#todo: scores based on variable inpupt
import numpy as np

from sklearn.model_selection import train_test_split
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis as LDA
from sklearn.metrics import roc_curve, roc_auc_score
import pandas as pd


def make_groups_equal_size(X, y):
    X_true = X[y == 1]
    y_true = y[y == 1]
    X_false = X[y == 0]
    y_false = y[y == 0]

    np.random.shuffle(X_true)
    np.random.shuffle(X_false)
    l = min([len(y_true), len(y_false)])
    X_true[:l, :]
    X_false[:l, :]
    X_ret = np.concatenate([X_true[:l, :], X_false[:l, :]])
    y_ret = np.concatenate([y_true[:l], y_false[:l]])
    return X_ret, y_ret


assert len(
    make_groups_equal_size(
        np.array([[1, 2, 3], [2, 3, 4], [3, 4, 5], [4, 5, 6]]),
        np.array([0, 0, 1, 1]))[0]) == 4
assert len(
    make_groups_equal_size(
        np.array([[1, 2, 3], [2, 3, 4], [3, 4, 5], [4, 5, 6]]),
        np.array([0, 0, 0, 1]))[0]) == 2


def prediction_rates(X_in,
                     y_in,
                     classifier=None,
                     n=5,
                     return_='score',
                     normalize_group_size=True,
                     verbosity=0,
                     test_size=0.4,
                     solver='eigen',
                     max_tries=2):
    '''
    X: training data
    y: target values
    classifier: classifier to use
    '''
    if classifier is None:
        pass
    else:
        raise ValueError("Not supported")
    score_all = []
    score_0 = []
    score_1 = []
    score_rocauc = []
    score_all_full_data = []
    score_0_full_data = []
    score_1_full_data = []
    score_rocauc_full_data = []
    value_counts = []
    classifier_ = []
    lv = 0

    X_train = X_test = y_train = y_test = []
    for x in range(n):
        #if bad data is selected (e.g. only one group): reselect
        while True:
            try:
                if normalize_group_size:
                    X, y = make_groups_equal_size(X_in, y_in)
                else:
                    X, y = X_in, y_in
                X_train, X_test, y_train, y_test = train_test_split(
                    X, y, test_size=test_size, random_state=x)
                #classifier = LDA(n_components=2, shrinkage = 'auto', solver = 'eigen', )
                classifier = LDA(n_components=1, shrinkage=None, solver=solver)

                classifier.fit(X_train, y_train)
                break
            except ValueError:
                if lv >= max_tries:
                    raise RuntimeError(
                        "Can't select data, that is accepted by estimator!")
                lv = lv + 1
                continue

        score_all.append(classifier.score(X_test, y_test))
        score_1.append(
            classifier.score(X_test[y_test == 1, :], y_test[y_test == 1]))
        score_0.append(
            classifier.score(X_test[y_test == 0, :], y_test[y_test == 0]))
        score_rocauc.append(
            roc_auc_score(y_test, np.dot(X_test, classifier.coef_.squeeze())))
        value_counts.append(pd.Series(y_train).value_counts().to_dict())
        if True:  #normalize_group_size:
            score_all_full_data.append(classifier.score(X_in, y_in))
            score_1_full_data.append(
                classifier.score(X_in[y_in == 1, :], y_in[y_in == 1]))
            score_0_full_data.append(
                classifier.score(X_in[y_in == 0, :], y_in[y_in == 0]))
            score_rocauc_full_data.append(
                roc_auc_score(y_in, np.dot(X_in, classifier.coef_.squeeze())))

        classifier_.append(classifier)

    score = (np.median(score_1) + np.median(score_0))

    if verbosity > 1:
        print('score all: max {} min {} mean {}'.format(max(score_all),
                                                        min(score_all),
                                                        np.mean(score_all)))
        print('score 1:   max {} min {} mean {}'.format(max(score_1),
                                                        min(score_1),
                                                        np.mean(score_1)))
        print('score 0:   max {} min {} mean {}'.format(max(score_0),
                                                        min(score_0),
                                                        np.mean(score_0)))
        print('score ROC-AUC:   max {} min {} mean {}'.format(
            max(score_rocauc), min(score_rocauc), np.mean(score_rocauc)))
        if True:  #normalize_group_size:
            print('score all full data: max {} min {} mean {}'.format(
                max(score_all_full_data), min(score_all_full_data),
                np.mean(score_all_full_data)))
            print('score 1 full data:   max {} min {} mean {}'.format(
                max(score_1_full_data), min(score_1_full_data),
                np.mean(score_1_full_data)))
            print('score 0 full data:   max {} min {} mean {}'.format(
                max(score_0_full_data), min(score_0_full_data),
                np.mean(score_0_full_data)))
            print('score ROC-AUC full data:   max {} min {} mean {}'.format(
                max(score_rocauc_full_data), min(score_rocauc_full_data),
                np.mean(score_rocauc_full_data)))
    if verbosity > 0:
        print(('score: {}'.format(score)))
        print('')

    if return_ == 'all':
        return dict(score_all = score_all, score_0 = score_0, score_1 = score_1, score = score, \
                    score_rocauc = score_rocauc, score_rocauc_full_data = score_rocauc_full_data, \
                    classifier_ = classifier_, value_counts = value_counts)
    elif return_ == 'score':
        return (score)


lda_prediction_rates = prediction_rates
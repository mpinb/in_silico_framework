"""Analyze the results of :py:mod:`simrun.reduced_model`

.. deprecated:: 0.4.0
    Analyzing synapse activations with LDA has been extended into :py:mod:`simrun.modular_reduced_model_inference`,
    where instead of LDA, we fit a raised cosine basis to the synapse activations.
    :py:mod:`simrun.modular_reduced_model_inference` is written to be more general, flexible,
    and performant. The latter was necessary in order to include the spatial resolution of synapse activations.

:skip-doc:

"""


#todo: scores based on variable inpupt
import numpy as np

from sklearn.model_selection import train_test_split
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis as LDA
from sklearn.metrics import roc_curve, roc_auc_score
import pandas as pd


def make_groups_equal_size(X, y):
    """Equally balance samples from :paramref:`X` based on the labels in :paramref:`y`.
    
    Randomly subsample a data matrix so that both classes have the same number of samples.
    The sample size will thus be twice the size of the smaller class.
    Only supports binary classification.
    
    Args:
        X (:py:class:`~numpy.array`): 2D array of features
        y (:py:class:`~numpy.array`): 1D array of labels
    
    Returns:
        tuple: subsampled 2D array of features and 1D array of labels
    """
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


def prediction_rates(
    X_in,
    y_in,
    classifier=None,
    n=5,
    return_='score',
    normalize_group_size=True,
    verbosity=0,
    test_size=0.4,
    solver='eigen',
    max_tries=2):
    '''Calculate the prediction rates of a binary classifier.
    
    For a given classifier, calclate the prediction rates for a given number of iterations :paramref:`n`.
    Returns the median of the prediction rates on each class
    
    Args:
        X_in (:py:class:`~numpy.array`): 2D test data: ``synapses x activations``
        y_in (:py:class:`~numpy.array`): 1D array of test labels (i.e. test labels)
        classifier (:py:class:`~sklearn.base.BaseEstimator`): LDA classifier to use.
        n (int): Amount of iterations for the prediction rates. One iteration is one train-test split.
        normalize_group_size (bool): If True, randomly subsample the data so that both classes have the same number of samples
        verbosity (int): Level of verbosity. Options are ``0`` (default), ``1``, or ``2``
        test_size (float): Fraction of the data to use as test data. Default is ``0.4``
        solver (str): Solver to use for LDA. Options are ``("svd", "lsqr", "eigen")``. Default is ``"eigen"``
        return_ (str): Return type. Options are ``("score", "all")``. Default is ``"score"``.
            'score' returns the median of the prediction rates for both classes. 
            'all' returns a dictionary of all scores, inlcuding the keys:
            
            - score_all: the prediction accuracy on all the data
            - score_0: the prediction accuracy on the negative class for :paramref:`n` random subsamples of the data
            - score_1: the prediction accuracy on the positive class for :paramref:`n` random subsamples of the data
            - score: the median of the prediction rates on each class
            - score_rocauc: the ROC-AUC score for :paramref:`n` random subsamples of the data
            - score_rocauc_full_data: the ROC-AUC score for the full data
            - classifier_: the classifier used for each iteration
            - value_counts: the value counts of the training data for each iteration
            
    Returns:
        float or dict: The median of the prediction rates for both classes or a dictionary of all scores
        
    See also:
        https://scikit-learn.org/stable/modules/generated/sklearn.discriminant_analysis.LinearDiscriminantAnalysis.html
        for available solvers for LDA.
    '''
    # TODO: this supports passing a classifier, but its overridden by an LDA initilization anyways?
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
        while True:
            try:  # make train-test split, fit classifier
                X, y = make_groups_equal_size(X_in, y_in) if normalize_group_size else (X_in, y_in)
                X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, random_state=x)
                #classifier = LDA(n_components=2, shrinkage = 'auto', solver = 'eigen', )
                classifier = LDA(n_components=1, shrinkage=None, solver=solver)
                classifier.fit(X_train, y_train)
                break
            except ValueError:  # Bad data is selected (e.g. contains only one class): reselect
                if lv >= max_tries:
                    raise RuntimeError("Can't select data, that is accepted by estimator!")
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
        return dict(
            score_all = score_all, 
            score_0 = score_0, 
            score_1 = score_1, 
            score = score,
            score_rocauc = score_rocauc, 
            score_rocauc_full_data = score_rocauc_full_data, 
            classifier_ = classifier_, 
            value_counts = value_counts)
    elif return_ == 'score':
        return (score)


lda_prediction_rates = prediction_rates
#!/usr/bin/env python3

import argparse
import json
import logging
import os
import pathlib
import shutil
import sys
import copy
import inspect
from collections import Counter
import itertools
import logging
import os

from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.cluster import KMeans
from sklearn import decomposition, preprocessing, random_projection
from sklearn.ensemble import RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.utils.validation import check_is_fitted
import numpy as np

import ruamel.yaml
from opusfilter import filters as filtermodule
import customfilter as customfiltermodule
from opusfilter.autogen_cluster import ScoreClusters
from opusfilter.classifier import load_dataframe
from opusfilter.opusfilter import OpusFilter
from sklearn import preprocessing
from sklearn.cluster import KMeans

logger = logging.getLogger(__name__)
logger.setLevel('INFO')
yaml = ruamel.yaml.YAML()

import matplotlib.pyplot as plt

from opusfilter.autogen import DefaultParameterFilters, PercentileFilters, ClusterFilters, ConfigurationGenerator, \
    FilterInspect
from opusfilter.util import yaml


def add_module(filters):
    for filter in filters:
        name = list(filter.keys())[0]
        if name.startswith('Custom'):
            filter['module'] = 'customfilter'

def get_score_file(input_files, filters, outputdir, sample_size, overwrite=False, max_length=150):
    """Calculate filter scores and return score file

    Remove duplicates and empty lines, take a sample of size n,
    produce filter scores file, and return its path.

    """
    config_gen = ConfigurationGenerator(files=[os.path.abspath(f) for f in input_files], workdir=outputdir)
    config_gen.add_remove_duplicates()
    config_gen.add_filter([{'LengthFilter': {'unit': 'word', 'min_length': 1, 'max_length': max_length}}])
    config_gen.add_subset(sample_size, 1)
    score_file = config_gen.add_score(filters)
    pre_config = config_gen.get_config()
    for step in pre_config['steps']:
        if step['type'] == 'filter' or step['type'] == 'score':
            add_module(step['parameters']['filters'])

    yaml.dump(pre_config, pathlib.Path(os.path.join(outputdir, 'config.yaml')))
    opusf = OpusFilter(pre_config)
    opusf.execute_steps(overwrite=overwrite)
    return os.path.join(outputdir, score_file)


def get_module(name):
    if name.startswith('Custom'):
        module = customfiltermodule
    else:
        module = filtermodule

    return module


class CustomScoreClusters(ScoreClusters):
    """
    Clustering that supports custom filters
    """

    def __init__(self, score_file, k=2):
        self.k = k
        self.df = load_dataframe(score_file)
        self.filters = {}
        for name in self.df.columns:
            first_part = name.split('.')[0]
            filter_cls = getattr(get_module(first_part), first_part)
            self.filters[name] = filter_cls
        self.scaler = preprocessing.StandardScaler()
        self.standard_data = self.scaler.fit_transform(self.df.mul(self.direction_vector))

        logger.info('Training KMeans with %s clusters', self.k)
        self.kmeans = KMeans(n_clusters=self.k, random_state=0, init='k-means++', n_init=1)
        self.kmeans.fit(self.standard_data)
        self.labels = self.kmeans.labels_
        self.cluster_centers = self.scaler.inverse_transform(self.kmeans.cluster_centers_) * self.direction_vector
        self._noisy_label = self._get_noisy_label()
        self.rejects = None
        self.thresholds = None

    def get_rejects(self):
        """Train random forest classifier to find important features

        Returns a list of booleans (True = reject).

        """

        logger.info('Skipping feature selection')
        return [False for _ in enumerate(self.df.columns)]

        logger.info('Training random forest')
        clf = RandomForestClassifier(random_state=1)
        clf.fit(self.standard_data, self.labels)
        logger.info('Finding important features')
        feature_importances = permutation_importance(clf, self.standard_data, self.labels)
        importance_mean_mean = np.mean(feature_importances.importances_mean)
        rej_coef = 0.1
        logger.info('* mean importance: %s', round(importance_mean_mean, 3))
        logger.info('* rejection coefficient: %s', rej_coef)
        logger.info('* decisions:')
        rejects = []
        for i, col in enumerate(self.df.columns):
            importance = feature_importances['importances_mean'][i]
            reject = importance < importance_mean_mean * rej_coef
            logger.info('  %s\t%s\t%s', col.ljust(25), round(importance, 3), 'reject' if reject else 'keep')
            rejects.append(reject)
        return rejects


def get_default_parameters(filter_name):
    """Get default parameters for a filter

    Uses the signature of the class. Arguments without default
    values are ignored and will cause a failure.

    """
    filter_cls = getattr(get_module(filter_name), filter_name)
    default_parameters = {}
    sig = inspect.signature(filter_cls)
    logger.info("signature: %s%s", filter_name, sig)
    for key, parameter in sig.parameters.items():
        if parameter.default == inspect.Signature.empty:
            if key != 'kwargs':
                logger.warning("Ignoring argument without default: %s", key)
            continue
        default_parameters[key] = parameter.default
    return default_parameters


class CustomFilterInspect(FilterInspect):
    def __init__(self, filterclass, filter_parameters=None):
        if isinstance(filterclass, str):
            self.filter_name = filterclass
            self.filter_cls = getattr(get_module(self.filter_name), self.filter_name)
        else:
            self.filter_name = filterclass.__name__
            self.filter_cls = filterclass
        self.initial_parameters = get_default_parameters(self.filter_name)
        if filter_parameters:
            self.initial_parameters.update(filter_parameters)


class CustomClusterFilters(ClusterFilters):
    """ Adds support for custom filters"""

    def set_filter_thresholds(self):
        """Get filter configuration with thresholds"""
        score_file = get_score_file(
            self.files, [{name: params} for name, params in self.filters_to_add], self.inter_dir, self.sample_size,
            overwrite=self.overwrite, max_length=self.max_length)
        self.scoredata = CustomScoreClusters(score_file, k=self.k)
        self._set_parameters(self.scoredata.get_result_df())
        if os.path.isfile(self.label_file_path) and not self.overwrite:
            logger.info('Label file "%s" exits, not overwriting', self.label_file_path)
        else:
            with open(self.label_file_path, 'w', encoding='utf-8') as label_file:
                for label in self.scoredata.labels:
                    label_file.write(str(label) + '\n')
        if self.use_tmp:
            shutil.rmtree(self.inter_dir)

    def _set_parameters(self, df):
        """Set filter parameters based on ScoreClusters

        thresholds: list of threshold values
        rejects: boolean-valued dictionary, dataframe columns as keys

        """
        self._filters = []
        for classname, params in self.filters_to_add:
            new_params = copy.deepcopy(params)
            filter_inspect = CustomFilterInspect(classname, new_params)
            column_prefix = classname
            if 'name' in params:
                column_prefix += '.' + params['name']
            df_part = df[df.name.str.startswith(column_prefix)]
            if all(df_part.reject):
                continue
            threshold_key = filter_inspect.find_threshold_keys(len(df_part))
            if threshold_key is None:
                continue
            thresholds = list(df_part['threshold'])
            for i, reject in enumerate(df_part.reject):
                if reject:
                    # Set a threshold that accepts all input
                    thresholds[i] = filter_inspect.filter_cls.accept_threshold
            new_params[threshold_key] = thresholds if len(thresholds) > 1 else thresholds[0]
            self._filters.append({classname: new_params})


if __name__ == '__main__':

    try:
        plt.style.use('seaborn-v0_8')
    except OSError:
        pass

    logger = logging.getLogger(__name__)

    logging.basicConfig(level=logging.INFO)
    logging.getLogger('mosestokenizer.tokenizer.MosesTokenizer').setLevel(logging.WARNING)

    parser = argparse.ArgumentParser(
        prog='opusfilter-autogen',
        description='Generate initial configuration based on parallel text data')

    parser.add_argument('--files', required=True, nargs='+', metavar='TEXTFILE', help='parallel text input file(s)')
    parser.add_argument('--langs', nargs='+', metavar='LANGCODE',
                        help='Language codes corresponding to the input files. If omitted, LanguageIDFilters will not be used.')
    parser.add_argument('--scripts', nargs='+', metavar='SCRIPT', help=(
        'Alphabetic scripts (e.g. Latin) corresponding to the input files. '
        'If omitted, CharacterScoreFilter will not be used.'))
    parser.add_argument('--method', choices=['defaults', 'percentiles', 'clustering'], default='clustering',
                        help='Method for selecting filter thresholds (default: %(default)s)')
    parser.add_argument('--sample-size', default=100000, type=int, metavar='INT',
                        help='Max number of sentence pairs used for data-based methods (default %(default)s)')
    parser.add_argument('--noisy-percentile', default=0.001, type=float, metavar='FLOAT',
                        help='Proportion of the data considered to be noisy; only for percentiles method (default %(default)s)')
    parser.add_argument('--clusters', '-k', default=2, type=int, metavar='INT',
                        help=(
                            'Number of clusters for the clustering method; try increasing if too much data is clustered '
                            'as noisy (default %(default)s)'))
    parser.add_argument('--work-dir', default='work',
                        help='Location of the source and target files for the generated configuration (default %(default)s)')
    parser.add_argument('--inter-dir',
                        help='Save intermediate files in this directory (use a temporary directory if not given)')
    parser.add_argument('--plot', metavar='PATH', default=None, type=str,
                        help=('Create histograms of feature data distributions and a scatter plot of the clustering; '
                              'give path to plot the PDF files to, or "-" for interactive plots; only for the clustering method'))
    parser.add_argument('--list-defaults', action='store_true',
                        help='List default filters of the method to the output and quit')
    parser.add_argument('--add-filter', nargs=2, action='append', default=[], metavar=('CLASS', 'JSON'),
                        help=('Instead of using default filters, add a filter of CLASS with JSON parameters object '
                              '("{}" for default parameters). The class name may be followed by a dot and a unique '
                              'filter identifier in order to allow multiple filters of the same class. Example: '
                              '--add-filter LanguageIDFilter.cld2 \'{"id_method": "cld2"}\''))
    parser.add_argument('--overwrite', action='store_true',
                        help='Overwrite existing intermediate files')
    parser.add_argument('-o', '--output', type=argparse.FileType('w'),
                        default='-', metavar='CONFIGFILE', help='Output configuration file (default %(default)s)')
    args = parser.parse_args()

    filters = [(name, json.loads(jsonstr)) for name, jsonstr in args.add_filter] if args.add_filter else None

    if args.method == 'clustering':
        filtergen = CustomClusterFilters(
            files=args.files, langs=args.langs, scripts=args.scripts, filters=filters,
            sample_size=args.sample_size, k=args.clusters, inter_dir=args.inter_dir, overwrite=args.overwrite)
    elif args.method == 'percentiles':
        filtergen = PercentileFilters(
            files=args.files, langs=args.langs, scripts=args.scripts, filters=filters,
            excluded_percentile=args.noisy_percentile, sample_size=args.sample_size,
            inter_dir=args.inter_dir, overwrite=args.overwrite)
    else:
        filtergen = DefaultParameterFilters(langs=args.langs, scripts=args.scripts, filters=filters)

    if args.list_defaults:
        yaml.dump(filtergen.DEFAULT_FILTERS, args.output)
        sys.exit(0)

    filters = filtergen.set_filter_thresholds()

    if args.method == 'clustering' and args.plot is not None:
        if args.plot == '-':
            filtergen.scoredata.plot(plt)
            plt.show()
        else:
            filtergen.scoredata.plot(plt, path=args.plot)

    generator = ConfigurationGenerator(
        files=[os.path.abspath(f) for f in args.files], langs=args.langs, workdir=args.work_dir)


    add_module(filtergen.filters)
    generator.add_filter(filtergen.filters)
    yaml.dump(generator.get_config(), args.output)

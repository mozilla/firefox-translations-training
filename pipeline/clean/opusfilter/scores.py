#!/usr/bin/env python3

import argparse
import logging
import sys

import json
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pandas import json_normalize

from pandas.plotting import scatter_matrix

from opusfilter.util import file_open
from opusfilter.util import lists_to_dicts


logger = logging.getLogger(__name__)


class ScoreCommands:

    def __init__(self, argv):
        parser = argparse.ArgumentParser(
            usage='''opusfilter-scores <command> [<args>]

Plot and diagnose filter scores

Subcommands:

list              Print score column names
describe          Print score statistics
corr              Plot score correlation matrix
hist              Plot score histograms
scatter-matrix    Plot scatter matrix for scores
values            Plot score values by line number

''')
        parser.add_argument('command', help='Subcommand to run')
        args = parser.parse_args(argv[:1])
        cmd = args.command.replace('-', '_')
        if not hasattr(self, cmd):
            logger.error('Unrecognized command "%s"', cmd)
            parser.print_help()
            exit(1)
        # use dispatch pattern to invoke method with same name
        getattr(self, cmd)(argv[1:])

    def _load_scores(self, fname, includefile=None):
        with file_open(fname, 'r') as fobj:
            df = json_normalize([lists_to_dicts(json.loads(line)) for line in fobj])
        if includefile:
            included = set(l.strip() for l in includefile.readlines())
            for col in df.columns:
                if col not in included:
                    logger.info('Excluding column %s', col)
                    df.drop(col, inplace=True, axis=1)
        return df

    def list(self, argv):
        parser = argparse.ArgumentParser(
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            description='Print score column names',
            usage='opusfilter-scores list [-h] scorefile')
        parser.add_argument('scorefile', type=str)
        args = parser.parse_args(argv)
        df = self._load_scores(args.scorefile)
        for col in df.columns:
            print(col)

    def describe(self, argv):
        parser = argparse.ArgumentParser(
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            description='Print score statistics',
            usage='opusfilter-scores describe [-h] scorefile')
        parser.add_argument('scorefile', type=str)
        parser.add_argument(
            '--percentiles', type=str,
            help='percentiles to include in the output (default "%(default)s")',
            default='.0001 .001 .01 .05 .1 .25 .5 .75 .9 .95 .99 .999 .9999')
        args = parser.parse_args(argv)
        percentiles = [float(x) for x in args.percentiles.split()]
        df = self._load_scores(args.scorefile)
        for col in df.columns:
            print('# {}'.format(col))
            print(df[col].describe(percentiles=percentiles))
            print()

    def scatter_matrix(self, argv):
        parser = argparse.ArgumentParser(
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            description='Plot scatter matrix',
            usage='opusfilter-scores scatter-matrix [-h] scorefile')
        parser.add_argument('scorefile', type=str)
        parser.add_argument('-i', '--include', type=argparse.FileType('r'), default=None,
                            help='Include only scores listed in file')
        parser.add_argument('--figsize', nargs=2, type=int, default=(9, 9),
                            help='Figure size (in inches)')
        parser.add_argument('--save_path', help='A path to the file save the plot', required=False)
        args = parser.parse_args(argv)
        df = self._load_scores(args.scorefile, args.include)
        # Remove columns with constant values (do not work with kde)
        for col in df.columns:
            if len(df[col].unique()) == 1:
                logger.info('Ignoring column %s with constant value', col)
                df.drop(col, inplace=True, axis=1)
        score_columns = list(df.columns)
        subplots = scatter_matrix(df, alpha=0.2, figsize=args.figsize, diagonal='kde')
        # Long score labels get easily overlapped, decrease size and
        # rotate to help a bit
        for ridx, row in enumerate(subplots):
            for cidx, ax in enumerate(row):
                if ridx == len(df.columns) - 1:
                    ax.set_xlabel(score_columns[cidx], rotation=30, fontsize=7)
                if cidx == 0:
                    ax.set_ylabel(score_columns[ridx], rotation=30, fontsize=7)

        if args.save_path is not None:
            plt.savefig(args.save_path)

    def corr(self, argv):
        parser = argparse.ArgumentParser(
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            description='Plot score correlation matrix',
            usage='opusfilter-scores corr [-h] scorefile')
        parser.add_argument('scorefile', type=str)
        parser.add_argument('-i', '--include', type=argparse.FileType('r'), default=None,
                            help='Include only scores listed in file')
        parser.add_argument('--figsize', nargs=2, type=int, default=(6, 6),
                            help='Figure size (in inches)')
        parser.add_argument('--save_path', help='A path to the file save the plot', required=False)

        args = parser.parse_args(argv)
        df = self._load_scores(args.scorefile, args.include)
        # Remove columns with constant values
        for col in df.columns:
            if len(df[col].unique()) == 1:
                logger.info('Ignoring column %s with constant value', col)
                df.drop(col, inplace=True, axis=1)
        score_columns = list(df.columns)
        corr = df.corr()
        fig = plt.figure(figsize=args.figsize)
        ax = fig.add_subplot(111)
        cmap = ax.matshow(corr)
        ticks = np.arange(len(score_columns))
        ax.set_xticks(ticks)
        ax.set_yticks(ticks)
        ax.xaxis.set_ticks_position('bottom')
        ax.set_xticklabels(score_columns, rotation=90, fontsize=7)
        ax.set_yticklabels(score_columns, fontsize=7)
        cb = fig.colorbar(cmap, ax=ax, fraction=0.046, pad=0.04)
        ax.set_title('Score correlations')
        fig.tight_layout()
        if args.save_path is not None:
            plt.savefig(args.save_path)

    def hist(self, argv):
        parser = argparse.ArgumentParser(
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            description='Plot score histograms',
            usage='opusfilter-scores hist [-h] scorefile')
        parser.add_argument('scorefile', type=str)
        parser.add_argument('-i', '--include', type=argparse.FileType('r'), default=None,
                            help='Include only scores listed in file')
        parser.add_argument('--bins', type=int, default=50, help='number of bins')
        parser.add_argument('--log', action='store_true', default=False, help='use logarithmic scale')
        parser.add_argument('--layout', nargs=2, type=int, default=None,
                            help='Number of rows and columns for the layout of the histograms')
        parser.add_argument('--figsize', nargs=2, type=int, default=(9, 9),
                            help='Figure size (in inches)')
        parser.add_argument('--save_path', help='A path to the file save the plot', required=False)

        args = parser.parse_args(argv)
        df = self._load_scores(args.scorefile, args.include)
        matplotlib.rcParams.update({'font.size': 7})
        df.hist(bins=args.bins, log=args.log, figsize=args.figsize, layout=args.layout)
        plt.tight_layout()
        if args.save_path is not None:
            plt.savefig(args.save_path)

    def values(self, argv):
        parser = argparse.ArgumentParser(
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            description='Plot score values by line number (one plot per score)',
            usage='opusfilter-scores values [-h] scorefile')
        parser.add_argument('scorefile', type=str)
        parser.add_argument('-i', '--include', type=argparse.FileType('r'), default=None,
                            help='Include only scores listed in file')
        parser.add_argument('--figsize', nargs=2, type=int, default=(11, 4),
                            help='Figure size (in inches)')
        parser.add_argument('--save_path', help='A path to the file save the plot', required=False)

        args = parser.parse_args(argv)
        df = self._load_scores(args.scorefile, args.include)
        score_columns = list(df.columns)
        for idx, col in enumerate(score_columns):
            fig = plt.figure(figsize=args.figsize)
            ax = fig.add_subplot(111)
            ax.plot(df.index, df[col])
            ax.set_title('{}'.format(col))
            fig.tight_layout()
        if args.save_path is not None:
            plt.savefig(args.save_path)

if __name__  == '__main__':
    logging.basicConfig(level=logging.INFO)
    ScoreCommands(sys.argv[1:])
    plt.show()

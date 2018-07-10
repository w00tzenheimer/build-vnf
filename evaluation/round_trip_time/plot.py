#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#

"""
About: Plot results of round trip time measurements.
"""

import os
import sys
sys.path.append('../scripts/')
import tex

import ipdb
import numpy as np

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.pyplot import cm
from scipy import stats

WARM_UP_NUM = 50
TOTAL_PACK_NUM = 500
FIG_FMT = 'png'


def calc_hwci(data, confidence=0.95):
    hwci = stats.sem(data) * stats.t._ppf((1+confidence)/2.0, len(data)-1)
    return hwci


def save_fig(fig, path, fmt=FIG_FMT):
    """Save fig to path"""
    fig.savefig(path + '.%s' % fmt, pad_iches=0,
                bbox_inches='tight', dpi=400, format=fmt)


def warn_x_std(value_arr, path=None, ret_inv_lst=False, x=3):
    """Raise exception if the value is not in the x std +- mean value of
    value_arr
    """
    avg = np.average(value_arr)
    std = np.std(value_arr)
    invalid_index = list()

    for idx, value in enumerate(value_arr):
        if (abs(value - avg) >= x * std):
            if not ret_inv_lst:
                if path:
                    error_msg = 'Line: %d, Value: %s is not located in three std range, path: %s' % (
                        (idx + 1), value, path)
                else:
                    error_msg = 'Line: %d, Value: %s is not located in three std range of list: %s' % (
                        (idx + 1), value, ', '.join(map(str, value_arr)))
                raise RuntimeError(error_msg)
            else:
                invalid_index.append(idx)

    print('[DEBUG] Len of value_arr: %d' % len(value_arr))
    return (value_arr, invalid_index)


def calc_rtt_lst(subdir, csv_tpl, var_lst, grp_step=10):
    rtt_result_lst = list()
    for var in var_lst:
        tmp_list = list()
        csv_name = csv_tpl % (var)
        csv_path = os.path.join(subdir, csv_name)
        rtt_arr = np.genfromtxt(csv_path, delimiter=',',
                                usecols=list(range(0, TOTAL_PACK_NUM))) / 1000.0

        rtt_arr = rtt_arr[:, WARM_UP_NUM:]
        # Calc hwci step by step to check if more measurements should be
        # performed
        print('Current CSV name: %s' % csv_name)
        for step in range(grp_step, rtt_arr.shape[0] + 1, grp_step):
            print('Current group step: %d' % step)
            step_rtt_arr = rtt_arr[:step, :]
            print('HWCI: %.10f'
                  % calc_hwci(np.average(step_rtt_arr, axis=1), 0.99))
        # Check nagative values
        signs = np.sign(rtt_arr).flatten()
        neg_sign = -1
        if neg_sign in signs:
            raise RuntimeError('Found negative RTT value in %s.' % csv_path)
        tmp_list = np.average(rtt_arr, axis=1)
        tmp_list, invalid_index = warn_x_std(tmp_list, csv_path,
                                             ret_inv_lst=True, x=3)
        if invalid_index:
            print('[WARN] Remove invalid rows from the CSV file')
            print('Invalid rows: %s' % ', '.join(map(str, invalid_index)))
            data = np.genfromtxt(csv_path, delimiter=',',
                                 usecols=list(range(0, TOTAL_PACK_NUM)))
            data = np.delete(data, invalid_index, axis=0)
            np.savetxt(csv_path, data, delimiter=',')
            raise RuntimeError('Found invalid rows, rows are already removed.' +
                               ' Run the plot program again')

        rtt_result_lst.append(
            # Average value and confidence interval
            (np.average(tmp_list), calc_hwci(tmp_list, confidence=0.99))
        )
    print('Final result list: ')
    print(rtt_result_lst)
    return rtt_result_lst


def label_bar(rects, ax):
    """
    Attach a text label above each bar displaying its height
    """
    for rect in rects:
        height = rect.get_height()
        ax.text(rect.get_x() + rect.get_width() / 2., 1.1*height,
                '%.3f' % height,
                ha='center', va='bottom')


def plot_ipd():
    tex.setup(width=1, height=None, span=False, l=0.15, r=0.98, t=0.98, b=0.17,
              params={
                  'hatch.linewidth': 0.5
              }
              )
    ipd_lst = [5]
    cmap = cm.get_cmap('tab10')

    # TODO: Improve the figure, techs and operations separately
    opts = ['FWD', 'ATS', 'XOR']

    techs = ['udp_rtt_' + x +
             '_%sms.csv' for x in (
                 'xdp_fwd_1400B', 'xdp_xor_1400B',
                 'lk_fwd_1400B',
                 'click_fwd_1400B', 'click_appendts_1400B', 'click_xor_1400B',
                 'dpdk_fwd_1400B', 'dpdk_appendts_1400B', 'dpdk_xor_1400B'
             )
             ]
    xtick_labels = (
        'XDP FWD', 'XDP XOR', 'Kernel FWD', 'Click FWD',
        'Click ATS',
        'Click XOR', 'DPDK FWD', 'DPDK ATS', 'DPDK XOR'
    )
    colors = [cmap(x) for x in range(len(techs))]
    hatch_patterns = ('x', 'xx', '+', '\\', '\\\\',
                      '\\\\\\\\', '/', '//', '///')
    bar_width = 0.08
    gap = 0.05
    fig, rtt_ax = plt.subplots()
    for idx, tech in enumerate(techs):
        rtt_result_lst = calc_rtt_lst('./results/rtt/', techs[idx], ipd_lst)
        rtt_bar = rtt_ax.bar([0 + idx * (bar_width + gap)], [t[0] for t in rtt_result_lst],
                             yerr=[t[1] for t in rtt_result_lst],
                             color=colors[idx], ecolor='red',
                             edgecolor='black', lw=0.6,
                             hatch=hatch_patterns[idx],
                             width=bar_width)
        label_bar(rtt_bar, rtt_ax)

    rtt_ax.set_ylabel('Round Trip Time (ms)')
    rtt_ax.set_xticks([0 + x * (bar_width + gap) for x in range(len(techs))])
    # rtt_ax.set_xticks([0, 0+bar_width+gap])
    rtt_ax.set_ylim(0, 0.5)
    rtt_ax.set_xticklabels(xtick_labels, fontsize=2.5)
    rtt_ax.grid(linestyle='--')

    rtt_ax.set_title('Sender UDP Payload size: 1400 Bytes')

    save_fig(fig, './rtt_fix_ipd')


if __name__ == '__main__':
    if len(sys.argv) == 3:
        FIG_FMT = sys.argv[2]
    elif sys.argv[1] == 'ipd':
        plot_ipd()
    else:
        raise RuntimeError('Unknown option!')

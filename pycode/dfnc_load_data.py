#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Oct 26 11:07:30 2017

@author: bbaker
"""
import scipy.io as sio
import numpy as np


def load_exemplar():
    TCDir = '/export/mialab/users/bbaker/projects/djica/tests3/IOTA/SIM/22Sep2017/increase_both/s2048-n64-nc20-r1/IC.mat'
    TC = sio.loadmat(TCDir)
    return TC['Shat_'][0]


def load_real_exemplar():
    TCDir = '/export/mialab/users/bbaker/projects/djica/tests3/final/s2016-n63-nc50-r1/IC.mat'
    TC = sio.loadmat(TCDir)
    return TC['Shat'][0]


def window_tc(TC, winsize, transpose=False):
    TC_w = []
    TC_v = []
    start = 0
    end = start + winsize
    while end <= TC.shape[0]:
        TT = TC[start:end, :]
        if transpose:
            TT = TT.T
        TC_w += [np.cov(TT.T)]
        TC_v += [np.var(TT.T)]
        start = start+1
        end = start+winsize
    TC_w = TC_w[TC_v.index(np.max(TC_v))]
    return [TC_w]


def window_all_tc(Shat_, winsize, n=0, transpose=False):
    Shat_w = []
    if n <= 0:
        n = len(Shat_)
    for i in range(n):
        # print(i)
        w = window_tc(Shat_[i], 50, transpose)
        Shat_w += w
    return Shat_w


if __name__ == '__main__':
    TC = load_real_exemplar()
    Shat_ = TC
    ws = 50
    Shat_w = window_all_tc(Shat_, ws, 10, transpose=True)
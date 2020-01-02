# -*- coding: utf-8 -*-
"""
Created on Thu Jan  2 14:30:11 2020

@author: rjaco
"""

import numpy as np
from epc_lib import epc_math

d_unamb = {20: 7500, 10: 15000, 5: 30000, 2.5: 60000, 1.25: 120000}

dcs = np.random.randint(1, 20, (10, 10, 4))

def calc_dist_phase1(dcs, led_mod_freq, d_offset):
    """
    Calculate the amplite and phase image from the dcs

    Parameters
    ----------
    dcs : numpy array, shape (height, 4, width)
        A numpy array containing the 4 DCS-images
    led_mod_freq : int
        The LED modulation frequency in MHz.
    d_offset : float
        Constant distant offset in milli meter

    Returns
    -------
    dist : numpy array
        The distance/amplitude image in milli meter.
    phase : numpy array
        The phase image in radians.

    """

    dcs = dcs.astype(float)
    phase = np.arctan2((dcs[:, :, 3] - dcs[:, :, 1]),
                       (dcs[:, :, 2] - dcs[:, :, 0]))
    phase += np.pi

    dist = d_unamb[led_mod_freq] / 2 / np.pi * phase  # unit mm
    dist += d_offset

    # take distance roll over into account
    dist[dist > d_unamb[led_mod_freq]] -= d_unamb[led_mod_freq]
    dist[dist < 0] += d_unamb[led_mod_freq]

    return dist.transpose(), phase.transpose()

dist1, phase1 = calc_dist_phase1(dcs, 20, 0)
dist2, phase2 = epc_math.calc_dist_phase(dcs, 20)

val1 = (dist1 == dist2).sum()
val2 = dist1.shape[0] * dist1.shape[1]

print("{} von {} Werten sind gleich".format(val1, val2))

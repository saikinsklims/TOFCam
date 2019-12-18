# -*- coding: utf-8 -*-
"""
Created on Sat Sep 28 10:24:57 2019

Math library for the epc project to calculate amplitude and phase images from
DCS-images as well as additional stuff.

@author: rjaco
"""

import numpy as np

# define variables
d_unamb = {20: 7.5, 10: 15, 5: 30, 2.5: 60, 1.25: 120}


def calc_dist_phase(dcs, led_mod_freq, d_offset):
    """
    Calculate the amplite and phase image from the dcs

    Parameters
    ----------
    dcs : numpy array, shape (height, 4, width)
        A numpy array containing the 4 DCS-images
    led_mod_freq : int
        The LED modulation frequency in MHz.
    d_offset : numpy array, shape (height, width)
        A numpy array containing the distance offset from the gray-image.
        Needs same shape as the DCSs

    Returns
    -------
    dist : numpy array
        The distance/amplitude image in meters.
    phase : numpy array
        The phase image in radians.

    """

    dcs = dcs.astype(float)
    phase = np.arctan2((dcs[:, :, 3] - dcs[:, :, 1]),
                       (dcs[:, :, 2] - dcs[:, :, 0]))
    phase += np.pi

    dist = d_unamb[led_mod_freq] / 2 / np.pi * phase + d_offset

    # take distance roll over into account
    dist[dist > d_unamb[led_mod_freq]] -= d_unamb[led_mod_freq]
    dist[dist < 0] += d_unamb[led_mod_freq]

    return dist.transpose()*1000, phase.transpose()


def calc_amplitude(dcs):
    """
    Calculate the signal amplitude from the dcs

    Parameters
    ----------
    dcs : numpy array, shape (height, 4, width)
        A numpy array containing the 4 DCS-images

    Returns
    -------
    ampl : numpy array
        Amplitude of the signal.

    """

    dcs = dcs.astype(float)
    ampl = 0.5 * np.sqrt((dcs[:, :, 3] - dcs[:, :, 1])**2 +
                         (dcs[:, :, 2] - dcs[:, :, 0])**2)

    return ampl.transpose()


def check_signal_quality(ampl, gray, exposure):
    """
    Evaluate the quality of the recorded dcs by checking the amplite

    Parameters
    ----------
    ampl : numpy array
        Amplitude of the signal.
    gray : numpy array
        Gray image.
    exposure: int
        Exposure time in us.

    Returns
    -------
    quality : int
        Description of the signal strength.
        -1: underexposed signal
        0: good signal
        1: overexposed signal
    noise : int
        Description of the SNR.
        -1: high noise
        0: good signal
    """
    quality = 0
    noise = 0

    exp_ref = 100
    sensitivity_bw = 0.25
    sensitivity_tof = 0.6

    e_bw = sensitivity_bw * exp_ref / exposure * gray
    e_tof = sensitivity_tof * exp_ref / exposure * ampl

    snr = 20 * np.log10(e_bw / e_tof)

    tmp1 = (snr < 70).sum()
    tmp2 = ampl.size - tmp1

    if (tmp2 > tmp1):
        quality = -1

    tmp1 = (ampl < 100).sum()
    tmp2 = (ampl < 2000).sum() - tmp1
    tmp3 = (2000 < ampl).sum()

    # too many under exposed pixels
    if (tmp1 > tmp2):
        quality = -1
    # too many overexposed pixels
    elif(tmp3 > tmp2):
        quality = 1

    # if there are no underexposed pixels reduce exposure a bit
    if (tmp1 < 1500):
        quality = 1

    return quality, noise


def distance_correction(dist, error_polynom):
    """
    Correction of the systematic distance error by polynom error fit

    Parameters
    ----------
    dist : numpy array
        The distance image.
    error_polynom : numpy array
        The error poylnom.

    Returns
    -------
    dist : numpy array
        The error corrected distance image.

    """
    dist = dist.astype('float32')
    error = np.polyval(error_polynom, dist)
    # neglect distances below 300
    dist = np.where(dist < 300, dist, dist-error)

    return dist

# -*- coding: utf-8 -*-
"""
Created on Sat Sep 28 10:22:11 2019

Script for algorithm development working with offline images

@author: rjaco
"""

import h5py
import numpy as np

from epc_lib import epc_math
from imgProc import imgProcScale

path = r'D:\HTW\Projektarbeit\300u_int_time_dcs_forward_90Deg.h5'

mod_frequ = 20
exposure = 250

# get the image stream
with h5py.File(path, 'r') as f:
    # List all groups
    a_group_key = list(f.keys())[0]

    # Get the data
    data = list(f[a_group_key])

# get height and width of images
height, _, width = data[0].shape

# create an empty offset-images and a random gray image
d_offset = np.zeros((height, width))
gray = np.random.rand(height, width) * 30

# convert the stream of dcs in distance, phase and amplitude
distance = []
phase = []
amplitude = []
for image in data:
    tmp1, tmp2 = epc_math.calc_dist_phase(image, mod_frequ, d_offset)
    distance.append(tmp1)
    phase.append(tmp2)
    amplitude.append(epc_math.calc_amplitude(image))

quality, noise = epc_math.check_signal_quality(amplitude[0], gray, exposure)

print(quality, noise)

# convert the images to height information
distance2 = [-x + x.max() for x in distance]

# show the shifting center of gravity in the image stream
for image in distance2:
    cog = imgProcScale.calc_image_cog(image, True)
    print(cog)


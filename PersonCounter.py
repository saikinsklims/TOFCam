# -*- coding: utf-8 -*-
"""
Created on Mon Oct 21 07:57:06 2019

@author: rjaco

Test-Script for person detection and moving direction
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib import animation
import pickle
import time

# load matrices
with open(r'mat_a.pkl', 'rb') as file:
    a = pickle.load(file)

with open(r'mat_b.pkl', 'rb') as file:
    b = pickle.load(file)

plot = False

if plot:
    fig, ax = plt.subplots()
    im = ax.imshow(a)
    # initialization function: plot the background of each frame
    def init():
        im.set_data(a)
        return [im]

    # animation function.  This is called sequentially
    def animate(i):
        a = im.get_array()
        a = np.roll(a, 1, axis=0)
        im.set_array(a)
        return [im]

    anim = animation.FuncAnimation(fig, animate, init_func=init,
                                   frames=200, interval=20, blit=True)

    plt.show()
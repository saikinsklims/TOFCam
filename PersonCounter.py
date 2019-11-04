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
import cv2

# load matrices
with open(r'mat_a.pkl', 'rb') as file:
    a = pickle.load(file)

with open(r'mat_b.pkl', 'rb') as file:
    b = pickle.load(file)

plot = False

if plot:
    mat_in = a
    fig, ax = plt.subplots()
    im = ax.imshow(mat_in)

    def init():
        """
        Initialization function for animation

        Returns
        -------
        list
            iterable of plot data.

        """
        im.set_data(mat_in)
        return [im]

    def animate(i):
        """
        Main animation function.  This is called sequentially

        Parameters
        ----------
        i : int
            Just a number.

        Returns
        -------
        list
            iterable of plot data.

        """
        tmp = im.get_array()
        tmp = np.roll(tmp, 1, axis=0)
        im.set_array(tmp)
        return [im]

    anim = animation.FuncAnimation(fig, animate, init_func=init,
                                   frames=200, interval=20, blit=True)

    plt.show()

# threshold image

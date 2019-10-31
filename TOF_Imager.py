# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
"""
Created on Sat Sep 28 10:22:11 2019

Main application script for the ToF Imager

@author: rjaco
"""

import os, sys
import numpy as np
import PyQt5 as Qt
from PyQt5.QtCore import QThread, pyqtSignal, pyqtSlot, QCoreApplication, QSize
from PyQt5.QtGui import QImage, QPixmap, QIntValidator, QIcon
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5 import uic

from collections import deque

import cv2
from epc_lib import epc_math
from imgProc import imgProcScale


# TODO for testing purposes only
import pdb
import h5py
import time
from itertools import cycle
path = r'D:\HTW\Projektarbeit\300u_int_time_dcs_forward_90Deg.h5'

mod_frequ = 20
exposure = 250

img_buffer_length = 10


class Thread(QThread):
    """
    Separate QThread that captures the camera images and after conversion
    emits a signal to the main application, containing the grabbed image

    Parameters
    ----------
    QThread : QThread
        The Thread itself.

    """

    cam = None
    running = False

    # signals
    change_pixmap = pyqtSignal(QImage)          # indicate redraw of image
    update_config = pyqtSignal(str, bool)       # request change of exposure
    update_gui = pyqtSignal(int)                # return changed exposure
    change_direction = pyqtSignal(int)          # indicate a change direction
    change_height = pyqtSignal(float, bool)     # indicate a new height
    new_person = pyqtSignal()                   # indicate a new person

    _auto = False
    _exposure = 1
    _update_cam = False
    _threshold = 0.2                            # objects taller than 0.2m only

    # image buffer for direction estimation
    _img_buffer = deque()

    # buffer for the position of the person
    _pos_buffer = None

    # TODO for testing purposes only
    with h5py.File(path, 'r') as f:
        # List all groups
        a_group_key = list(f.keys())[0]

        # Get the data
        data = list(f[a_group_key])

    data = [x.transpose() for x in data]

    # TODO check correct dimensions
    # get height and width of images
    height, _, width = data[0].shape

    # create an empty offset-images and a random gray image
    d_offset = np.zeros((height, width))
    gray = np.random.rand(height, width) * 30

    def _get_height(self, image, background):
        """
        Calculate the height of the object in the distance image.

        Parameters
        ----------
        image : numpy array
            The distance image.
        background : numpy array
            The background image.

        Returns
        -------
        height : float
            The calculated height of the object.
        correct_height: bool
            Check if height is within the correct position
        pos : numpy array
            Position of the person

        """
        height = 0

        base_height = np.mean(background)

        # thresholding first
        image[image > background - self._threshold] = base_height

        # shift and flip
        image = -(image - base_height)

        # some gaussian blurring
        img_blur = cv2.GaussianBlur(image, (5, 5), 2)

        # get the height
        height = np.max(img_blur)
        height = round(height, 2)

        # get x-position of height
        tmp_pos = np.argmax(img_blur)
        pos = np.unravel_index(tmp_pos, img_blur.shape)
        correct_height = False
        # TODO check correct position for correct height calculation
        if (50 < pos[1] < 100):
            correct_height = True
        return height, correct_height, pos

    def _get_direction(self, image, background):
        """
        Calculate the direction of the moving object in the given image.

        Parameters
        ----------
        image : numpy array
            The current image.
        background: numpy array
            The background.

        Returns
        -------
        direction : int
            Direction indicator: left      -> 0,
                                 right     -> +1.
                                 undefined -> -1

        """
        direction = -1
        # get the 5th last image and get the center of gravity
        img_last = self._img_buffer.popleft()
        cog = imgProcScale.calc_image_cog(img_last, background,
                                          False, self._threshold)

        # calculate cog of new image and calculate difference
        cog -= imgProcScale.calc_image_cog(image, background,
                                           False, self._threshold)

        if cog[0] > 0:
            direction = 0
        elif cog[0] < 0:
            direction = 1

        # append the current image to the image buffer
        self._img_buffer.append(image)

        return direction

    def stop(self):
        """
        Request the thread to stop by changing the while-loop control

        Returns
        -------
        None.

        """
        self.running = False

        # disconnect the slots
        self.update_config.disconnect()

    def run(self):
        """
        Called by Thread.start(); actually containing the work.

        Returns
        -------
        None.

        """
        self.running = True

        # connect the slots
        self.update_config.connect(self._update_exposure)

        # TODO for testing only # FIXME replace with actual image capture
        pool = cycle(self.data)

        # fill the dist image buffer
        for idx in range(img_buffer_length):
            img = next(pool)
            dist, phase = epc_math.calc_dist_phase(img, mod_frequ, 0)
            self._img_buffer.append(dist)

        # put a dist image in the average buffer
        img_sum = dist.astype('float64')
        img_count = 1

        while self.running:
            # TODO image capture
            time.sleep(0.2)
            img = next(pool)

            if img is not None:
                img_count += 1

                # calculate distance and phase
                dist, phase = epc_math.calc_dist_phase(img, mod_frequ, 0)
                ampl = epc_math.calc_amplitude(img)

                # put the image into the average
                img_sum += dist
                img_avg = np.round(img_sum / img_count)

                # img_view = self._exposure * img_view        # FIXME

                # get some quality measures
                quality, noise = epc_math.check_signal_quality(ampl,
                                                               self.gray,
                                                               self._exposure)

                height, pos_correct, pos = self._get_height(dist.copy(), img_avg)
                self.change_height.emit(height, pos_correct)

                direction = self._get_direction(dist.copy(), img_avg)
                self.change_direction.emit(direction)

                # normalize gray image and convert to QImage and scale
                img_view = dist.copy()
                cv2.normalize(dist, img_view, 0, 255, cv2.NORM_MINMAX)
                img_view = img_view.astype('uint8')
                height, width = img_view.shape
                # draw a circle aroud person, but only if taller than 0.5m
                if height > 0.5:
                    img_view = cv2.circle(img_view, (pos[1], pos[0]), 10, 128)
                # TODO check correct position orientation
                convertToQtFormat = QImage(img_view, width, height,
                                           QImage.Format_Grayscale8)
                p = convertToQtFormat.scaled(4*width, 4*height,
                                             Qt.QtCore.Qt.IgnoreAspectRatio)

                # request an update of the image in the viewer
                self.change_pixmap.emit(p)

                # it is a new person, when the person is suddenly at a
                # different place
                if self._pos_buffer is not None & height > 0.5:
                    tmp = self._pos_buffer
                    diff_x = abs(tmp[0] - pos[0])
                    if diff_x > 30:
                        self.new_person.emit()

                self._pos_buffer = pos

            # check if the exposure settings need to be updated

            # if auto exposure
            # TODO incorperate noise estimate and control that as well
            if self._auto:
                # increase exposure until pixel intensity is good
                if quality < 0:
                    self._exposure += 1
                elif quality > 0:
                    self._exposure -= 1
                self._update_cam = True

            if self._update_cam:
                # TODO change camera settings
                self.update_gui.emit(self._exposure)
                self._update_cam = False

    @pyqtSlot(str, bool)
    def _update_exposure(self, value, auto):
        """
        Slot that triggers the camera exposure update during the live view.

        Parameters
        ----------
        value : string
            The new exposure setting.
        auto : bool
            Use auto exposure

        Returns
        -------
        None.

        """
        self._exposure = int(value)
        self._auto = auto

        # request change of settings in next cycle
        self._update_cam = True


class App(QMainWindow):
    """
    The main application Window.

    Parameters
    ----------
    QMainWindow : QMainWindow
        The window itself.

    """

    def __init__(self):
        """
        Constructor that loads the user interface.

        Returns
        -------
        None.

        """
        super().__init__()
        uic.loadUi('TOF_Imager.ui', self)

        self.th = Thread(self)

        # exposure settings only numerical
        validator = QIntValidator(1, 10000)
        self.exposure_LineEdit.setValidator(validator)

        # connect the widgets to the slots
        self.quit_Button.clicked.connect(self._quit_app)
        self.capture_live_Button.clicked.connect(self._start_live)
        self.stop_live_Button.clicked.connect(self._stop_live)
        self.th.update_gui.connect(self._update_exposure_gui)
        self.exposure_LineEdit.editingFinished.connect(self._change_exposure)
        self.auto_exposure_CheckBox.stateChanged.connect(self._change_exposure)
        self.th.change_pixmap.connect(self._set_image)
        self.th.change_direction.connect(self._show_direction)
        self.th.change_height.connect(self._show_height)
        self.th.new_person.connect(self._increment_Counter)

        # hide the line widgets
        self.line_up.setVisible(False)
        self.line_down.setVisible(False)

        # set the initial height info
        self.height_label.setText('0 m')
        self.height_label.setStyleSheet("QLabel { background-color : red; color : black; }")

        self.capture_live_Button.setIcon(QIcon("start.png"))
        self.capture_live_Button.setIconSize(QSize(50, 50))

        self.stop_live_Button.setIcon(QIcon("stop.png"))
        self.stop_live_Button.setIconSize(QSize(50, 50))
        self.stop_live_Button.setEnabled(False)

        self.counter = 0

    @pyqtSlot(float, bool)
    def _show_height(self, height, correct_height):
        """
        Display the new height.

        Parameters
        ----------
        height : float
            The new height.
        correct_height: bool
            Indicator if height position is correct.

        Returns
        -------
        None.

        """
        self.height_label.setText('{0:.2f} m'.format(height))

        if correct_height:
            self.height_label.setStyleSheet("QLabel { background-color : green; color : white; }")
        else:
            self.height_label.setStyleSheet("QLabel { background-color : red; color : black; }")

    @pyqtSlot()
    def _increment_Counter(self):
        """
        Increment the person counter and show the new count.

        Returns
        -------
        None.

        """
        self.counter += 1
        self.count_label.setText('{}'.format(self.counter))

    @pyqtSlot(int)
    def _show_direction(self, direction):
        """
        Slot that changes the direction indicators.

        Parameters
        ----------
        direction : int
            The direction.

        Returns
        -------
        None.

        """
        if direction != -1:
            self.line_up.setVisible(bool(direction))
            self.line_down.setVisible(not bool(direction))
        else:
            self.line_up.setVisible(False)
            self.line_down.setVisible(False)

    @pyqtSlot(QImage)
    def _set_image(self, image):
        """Slot that changes the shown image by setting the pixmap.

        Parameters
        ----------
        image : QImage
            The image.

        """
        self.image_View.setPixmap(QPixmap.fromImage(image))

    @pyqtSlot()
    def _change_exposure(self):
        """
        Is triggered when the user changes the exposure settings.

        Returns
        -------
        None.

        """
        value = self.exposure_LineEdit.text()
        flag = bool(self.auto_exposure_CheckBox.isChecked())
        self.exposure_LineEdit.setEnabled(not flag)

        # request a change of the configuration
        self.th.update_config.emit(value, flag)

    @pyqtSlot(int)
    def _update_exposure_gui(self, value):
        """
        Is triggered when the capturing thread has changed the exposure
        settings.

        Parameters
        ----------
        value : int
            The current exposure.

        Returns
        -------
        None.

        """
        # set the new exposure
        self.exposure_LineEdit.setText(str(value))

    @pyqtSlot()
    def _start_live(self):
        """
        Start the live capturing of the ToF images.

        Returns
        -------
        None.

        """
        self.capture_live_Button.setEnabled(False)
        self.stop_live_Button.setEnabled(True)

        # start the capture
        self.th.start()

    def _stop_live(self):
        """
        Stop the live capturing of the ToF images.

        Returns
        -------
        None.

        """
        self.capture_live_Button.setEnabled(True)
        self.stop_live_Button.setEnabled(False)

        # stop capture
        self.th.stop()

    @pyqtSlot()
    def _quit_app(self):
        """
        Close the app and destroy all resources.

        Returns
        -------
        None.

        """
        self.close()
        QCoreApplication.quit()


if __name__ == '__main__':
    if not os.path.exists('TOF_Imager.ui'):
        print('No ui-file found')
        exit()
    app = QApplication(sys.argv)
    ex = App()
    ex.show()
    sys.exit(app.exec_())

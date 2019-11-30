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
from epc_lib import epc_server, epc_image
from epc_lib import epc_math
from imgProc import imgProcScale
from imager import imager


# TODO for testing purposes only
import pdb
import pickle
import time
from itertools import cycle
path1 = r'C:\Users\rjaco\Google Drive\Praxisprojekt - TOF-Kamera\Software\samples\distImageWithMotion.p'
path2 = r'C:\Users\rjaco\Google Drive\Praxisprojekt - TOF-Kamera\Software\samples\ampImageWithMotion.p'

mod_frequ = 10

img_direction_buffer_length = 10
image_avg_buffer_length = 500

height_correction_scale = 0.9447
height_correction_offset = 341


class Thread(QThread):
    """
    Separate QThread that captures the camera images and after conversion
    emits a signal to the main application, containing the grabbed image

    Parameters
    ----------
    QThread : QThread
        The Thread itself.

    """

    # signals
    change_pixmap = pyqtSignal(QImage, QImage)  # indicate redraw of image
    update_config = pyqtSignal(str, bool)       # request change of exposure
    update_gui = pyqtSignal(int)                # return changed exposure
    change_direction = pyqtSignal(int)          # indicate a change direction
    change_height = pyqtSignal(float, bool)     # indicate a new height
    new_person = pyqtSignal()                   # indicate a new person

    def __init__(self, QThread):
        """
        Constructor

        Parameters
        ----------
        QThread : QThread
            The parent thread.

        Returns
        -------
        None.

        """
        super().__init__()
        self._cam = None
        self._running = False

        # TODO
        try:
            # Ethernet connection
            self._server = epc_server('192.168.1.80')
            self._image_epcDev = epc_image(self._server)
            imager.imagerInit(self._server, self._image_epcDev)
            self._cam = True
        except Exception as e:
            print("[INFO]: Cant connect to server")
            print(str(e))
            self._cam = False

        self.auto_background = False            # flag for auto background
        self._auto_exposure = False             # flag for auto exposure
        self._exposure = 1                      # exposure value
        self._update_cam = False                # flag when cam needs update
        self._threshold = 200                   # objects taller than 0.2m only

        # image buffer for direction estimation
        self._img_buffer = deque()

        # buffer for the position of the person
        self._pos_buffer = []

        # buffer for the moving average
        self._img_avg_buffer = deque(maxlen=image_avg_buffer_length)

        # TODO for testing purposes only
        # with open(path1, 'rb') as file:
        #     data_dist = pickle.load(file)
        #     self._cam = True
        # with open(path2, 'rb') as file:
        #     data_ampl = pickle.load(file)

        # self.pool_data = cycle(data_dist)
        # self.pool_ampl = cycle(data_ampl)

        # get height and width of images
        height, width = 60, 160

        # create random gray image
        self._gray = np.random.rand(height, width)

        # create a zero background image
        self._background = np.zeros((height, width))

        # connect the slots
        self.update_config.connect(self._update_exposure)

    @pyqtSlot()
    def set_background(self):
        """
        Capture an image from the hardware and set as background.

        Returns
        -------
        None.

        """
        if self._cam:
            dist, phase, ampl = self._get_image()
            self._background = dist

            dist = dist / dist.max() * 255
            dist = dist.astype('uint8')
            img_height, img_width = dist.shape
            convertToQtFormat = QImage(dist, img_width, img_height,
                                       QImage.Format_Grayscale8)
            q = convertToQtFormat.scaled(4*img_width, 4*img_height,
                                         Qt.QtCore.Qt.IgnoreAspectRatio)

            # request an update of the image in the viewer
            self.change_pixmap.emit(q, q)

    def _get_image(self):
        """
        Get the next image from the hardware.

        Returns
        -------
        dist : numpy array
            The distance image.
        phase : numpy array
            The phase image.
        ampl : numpy array
            The amplitude image.

        """
        # capture image from hardware
        img = self._image_epcDev.getDCSs()
        # calculate the distance, phase and amplitude
        dist, phase = epc_math.calc_dist_phase(img, mod_frequ, 0)
        ampl = epc_math.calc_amplitude(img)

        # TODO for testing
        # dist = next(self.pool_data).astype('float32')
        # phase = dist.copy()
        # ampl = next(self.pool_ampl).astype('float32')
        # time.sleep(0.5)

        # do some noise suppresion
        dist = dist.astype('float32')
        dist = cv2.medianBlur(dist, 7)

        return dist, phase, ampl

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
        img_blur = cv2.GaussianBlur(image, (15, 5), 7)

        # get the height
        height = np.max(img_blur)
        height = round(height, 2)

        # correction of systematic linear height error
        height = self._height_correction(height)

        # get x-position of height
        tmp_pos = np.argmax(img_blur)
        pos = np.unravel_index(tmp_pos, img_blur.shape)
        correct_height = False
        # check correct position for correct height calculation
        if (50 < pos[1] < 100):
            correct_height = True
        return height, correct_height, pos

    def _height_correction(self, height):
        """
        Correct the given height according to the polynomial correction

        Parameters
        ----------
        height : float
            The height to be corrected.

        Returns
        -------
        height_corrected : float
            The corrected height.

        """
        height_corrected = height * height_correction_scale
        height_corrected -= height_correction_offset

        return height_corrected

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
        self._running = False

    def run(self):
        """
        Called by Thread.start(); actually containing the work.

        Returns
        -------
        None.

        """
        self._running = True

        # fill the dist image buffer
        for idx in range(img_direction_buffer_length):
            dist, phase, ampl = self._get_image()
            self._img_buffer.append(dist)

        # put a dist image in the average buffer
        self._img_avg_buffer.append(dist)

        while self._running and self._cam:

            dist, phase, ampl = self._get_image()

            if dist is not None:

                # put the image into the average
                if self.auto_background:
                    self._img_avg_buffer.append(dist)
                    img_avg = 0
                    for element in self._img_avg_buffer:
                        img_avg += element

                    img_avg /= len(self._img_avg_buffer)
                else:
                    img_avg = self._background

                # get some quality measures
                quality, noise = epc_math.check_signal_quality(ampl,
                                                               self._gray,
                                                               self._exposure)
                # change exposure time if required by quality check
                if quality == -1 and self._auto_exposure:
                    self._exposure = self._exposure * 1.25
                    # clip exposure at 4000 due to hardware limit
                    if self._exposure > 4000:
                        self._exposure = 4000
                    self._update_cam = True
                elif quality == 1 and self._auto_exposure:
                    self._exposure = self._exposure * 0.9
                    self._update_cam = True

                # get the height and the height position
                height, pos_correct, pos = self._get_height(dist.copy(),
                                                            img_avg)
                self.change_height.emit(height, pos_correct)

                # get the direction
                direction = self._get_direction(dist.copy(), img_avg)
                self.change_direction.emit(direction)

                # normalize gray image and convert to QImage and scale
                img_view = dist.copy()
                img_view = img_view / 2**12 * 255
                img_view = img_view.astype('uint8')
                img_height, img_width = img_view.shape
                img_view = cv2.cvtColor(img_view, cv2.COLOR_GRAY2BGR)
                # draw a circle aroud person, but only if taller than 0.5m
                if height > 200:
                    img_view = cv2.circle(img_view, (pos[1], pos[0]),
                                          10, (0, 0, 255))

                convertToQtFormat = QImage(img_view, img_width, img_height,
                                           QImage.Format_RGB888)
                p = convertToQtFormat.scaled(4*img_width, 4*img_height,
                                             Qt.QtCore.Qt.IgnoreAspectRatio)

                background = img_avg.copy()
                background = background / background.max() * 255
                background = background.astype('uint8')
                convertToQtFormat = QImage(background, img_width, img_height,
                                           QImage.Format_Grayscale8)
                q = convertToQtFormat.scaled(4*img_width, 4*img_height,
                                             Qt.QtCore.Qt.IgnoreAspectRatio)

                # request an update of the image in the viewer
                self.change_pixmap.emit(p, q)
                # it is a new person, when the person is suddenly at a
                # different place and taller than 1000
                if self._pos_buffer == [0, 0] and height > 1000:
                    # tmp = self._pos_buffer
                    # diff_x = abs(tmp[0] - pos[0])
                    # if diff_x > 30:
                    self.new_person.emit()
                elif height < 1000:
                    pos = [0, 0]
                self._pos_buffer = pos

            if self._update_cam:
                self._server.sendCommand('setIntegrationTime2D {}'.format(self._exposure))	 # t_int in us
                self._server.sendCommand('setIntegrationTime3D {}'.format(self._exposure))	  # t_int in us
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
        self._auto_exposure = auto

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
        self.auto_background_CheckBox.stateChanged.connect(self._auto_background)
        self.auto_exposure_CheckBox.stateChanged.connect(self._change_exposure)
        self.set_background_Button.clicked.connect(self.th.set_background)
        self.reset_counter_Button.clicked.connect(self._reset_counter)
        self.th.change_pixmap.connect(self._set_image)
        self.th.change_direction.connect(self._show_direction)
        self.th.change_height.connect(self._show_height)
        self.th.new_person.connect(self._increment_counter)

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

        self._counter = 0

    @pyqtSlot()
    def _reset_counter(self):
        """
        Reset the person counter.

        Returns
        -------
        None.

        """
        self._counter = -1
        self._increment_counter()

    @pyqtSlot(int)
    def _auto_background(self, state):
        """
        Is triggered when the auto background checkbox is un/checked. Sets
        the auto background flag in the acquisition thread.

        Parameters
        ----------
        state : int
            CheckState of the CheckBox.

        Returns
        -------
        None.

        """
        if state == 2:
            self.th.auto = True
        elif state == 0:
            self.th.auto = False

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
        self.height_label.setText('{0:.2f} mm'.format(height))

        if correct_height:
            self.height_label.setStyleSheet("QLabel { background-color : green; color : white; }")
        else:
            self.height_label.setStyleSheet("QLabel { background-color : red; color : black; }")

    @pyqtSlot()
    def _increment_counter(self):
        """
        Increment the person counter and show the new count.

        Returns
        -------
        None.

        """
        self._counter += 1
        self.count_label.setText('{}'.format(self._counter))

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

    @pyqtSlot(QImage, QImage)
    def _set_image(self, image, background):
        """Slot that changes the shown image by setting the pixmap.

        Parameters
        ----------
        image : QImage
            The image.
        background: QImage
            The Background image.

        """
        self.image_View.setPixmap(QPixmap.fromImage(image))
        self.background_View.setPixmap(QPixmap.fromImage(background))

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
        self.set_background_Button.setEnabled(False)
        self.auto_background_CheckBox.setEnabled(False)

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
        self.set_background_Button.setEnabled(True)
        self.auto_background_CheckBox.setEnabled(True)

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
    if not QApplication.instance():
        app = QApplication(sys.argv)
    else:
        app = QApplication.instance()
    ex = App()
    ex.show()
    app.exec_()

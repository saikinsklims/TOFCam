# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
"""
Created on Sat Sep 28 10:22:11 2019

Main application script for the ToF Imager

@author: rjaco
"""

import os, sys
import PyQt5 as Qt
from PyQt5.QtCore import QThread, pyqtSignal, pyqtSlot, QCoreApplication
from PyQt5.QtGui import QImage, QPixmap, QIntValidator
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox, QFileDialog, QLineEdit
from PyQt5 import uic

import cv2

import pdb

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

    _auto = False
    _exposure = 0
    _update_cam = False

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

        while self.running:
            # img = self.cam.getImage()
            # if img is not None:
            #     img_view = img.copy()
            #     cv2.normalize(img, img_view, 0, 255, cv2.NORM_MINMAX)
            #     img_view = img_view.astype('uint8')
            #     convertToQtFormat = QImage(img_view, img_view.shape[1],
            #                                img_view.shape[0], QImage.Format_Grayscale8)
            #     p = convertToQtFormat.scaled(816, 683, Qt.QtCore.Qt.KeepAspectRatio)
            #     self.change_pixmap.emit(p)
            # check if the exposure settings need to be updated

            #TODO image capture

            # if auto exposure
            if self._auto:
                #TODO auto exposure
                self._update_cam = True

            if self._update_cam:
                #TODO change camera settings
                print("changing exposure to: ", self._exposure)
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
        self.th.update_gui.connect(self._update_exposure_gui)
        self.exposure_LineEdit.editingFinished.connect(self._change_exposure)
        self.auto_exposure_CheckBox.stateChanged.connect(self._change_exposure)

    @pyqtSlot()
    def _change_exposure(self):
        """
        Is triggered when the user changes the exposure settings.

        Returns
        -------
        None.

        """
        value = self.exposure_LineEdit.text()
        flag = self.auto_exposure_CheckBox.checkState()

        # request a change of the configuration
        self.th.update_config.emit(value, flag)

    @pyqtSlot(int)
    def _update_exposure_gui(self, value):
        """
        Is triggered when the capturing thread has changed the exposure settings.

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
        self.capture_live_Button.setText("Stop Live View")

        # reconnect the button to a different action
        self.capture_live_Button.clicked.disconnect(self._start_live)
        self.capture_live_Button.clicked.connect(self._stop_live)

        # start the capture
        self.th.start()

    def _stop_live(self):
        """
        Stop the live capturing of the ToF images.

        Returns
        -------
        None.

        """
        self.capture_live_Button.setText("Start Live View")

        # reconnect the button to a different action
        self.capture_live_Button.clicked.disconnect(self._stop_live)
        self.capture_live_Button.clicked.connect(self._start_live)

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
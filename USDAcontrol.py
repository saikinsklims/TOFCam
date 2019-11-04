"""Main script for the USDA control application

   Set the correct filter positions at the beginning of the file.

   @author: rainer.jacob

   Requirements:
    - PyQT5
    - openCV (cv2)
    - pypylon
    - pythonnet
    - pythoncom
    - h5py
"""
# pylint: disable=no-name-in-module,invalid-name,c-extension-no-member,wrong-import-position
# pylint: disable=line-too-long
import sys
import os
import collections
import datetime

import numpy as np

import h5py
import PyQt5 as Qt
from PyQt5.QtCore import QThread, pyqtSignal, pyqtSlot, QCoreApplication, QRegExp
from PyQt5.QtGui import QImage, QPixmap, QIntValidator, QRegExpValidator
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox, QFileDialog, QLineEdit
from PyQt5 import uic
# fix OLE initialize error https://github.com/pythonnet/pythonnet/issues/439
import pythoncom
pythoncom.CoInitialize() # pylint: disable=no-member

import cv2
import clr
clr.AddReference("OptecHID_FilterWheelAPI")
from cottonem import image_acquisition

class ExtLineEdit(QLineEdit):
    """Extension of the QLineEdit-Widget by a custom event, reacting on mouse click.

    Parameters
    ----------
    QLineEdit : QLineEdit
        Base class

    """

    clicked = pyqtSignal()

    def __init__(self, parent):
        QLineEdit.__init__(self, parent)

    def mousePressEvent(self, QMouseEvent):
        """Reroute the mouse press event to emit the customized signal

        Parameters
        ----------
        QMouseEvent : QMouseEvent
            Base class of the event

        """

        self.clicked.emit()

class Thread(QThread):
    """Separate QThread that captures the camera images and after conversion
    emits a signal to the main application, containing the grabbed image

    Parameters
    ----------
    QThread : QThread
        The Thread itself.

    """

    cam = None
    camWheelPosition = 0
    changePixmap = pyqtSignal(QImage)
    running = False

    updateConfig = pyqtSignal(str, str)
    updateConfigSuccess = pyqtSignal(bool)

    _sender = 0
    _exposure = 0
    _updateCam = False

    def stop(self):
        """Request the thread to stop by changing the while-loop control
        """

        self.running = False
        self.updateConfig.disconnect()
        self.cam.stop()

    def run(self):
        """Called by Thread.start(); actually containing the work.

        """
        self.running = True
        self.cam.setPosition(self.camWheelPosition)
        self.updateConfig.connect(self._updateExposure)
        self.cam.start()
        while self.running:
            img = self.cam.getImage()
            if img is not None:
                img_view = img.copy()
                cv2.normalize(img, img_view, 0, 255, cv2.NORM_MINMAX)
                img_view = img_view.astype('uint8')
                convertToQtFormat = QImage(img_view, img_view.shape[1],
                                           img_view.shape[0], QImage.Format_Grayscale8)
                p = convertToQtFormat.scaled(816, 683, Qt.QtCore.Qt.KeepAspectRatio)
                self.changePixmap.emit(p)
            # check if the exposure settings need to be updated
            if self._updateCam:
                self.cam.stop()
                ret = self.cam.updateCameraConfig({self._sender: {'ExposureTime': self._exposure * 1000}})
                if ret:
                    self._updateCam = False
                    self.updateConfigSuccess.emit(True)
                    self.cam.start()
                else:
                    self._updateCam = False
                    self.updateConfigSuccess.emit(False)
                    self.cam.start()

    @pyqtSlot(str, str)
    def _updateExposure(self, value, sender):
        """Slot that triggers the camera exposure update during the live view.

        Parameters
        ----------
        value : string
            The new exposure setting.
        sender : str
            The exposure ID

        """

        self._exposure = int(value)
        self._sender = int(sender)
        self._updateCam = True


class App(QMainWindow):
    """The main application Window.

    Parameters
    ----------
    QMainWindow : QMainWindow
        The window itself.

    """

    updateConfigSucces = pyqtSignal(bool)

    def __init__(self):
        """The constructor that loads the user interface and connects
        the Widgets to the corresponding signals/slots.

        """

        super().__init__()
        uic.loadUi('USDAcontrol.ui', self)

        # add an aditional extended QLineEdit for the path settings
        self.pathLineEdit = ExtLineEdit(self.frame)
        self.pathLineEdit.setGeometry(Qt.QtCore.QRect(180, 130, 131, 31))
        font = Qt.QtGui.QFont()
        font.setPointSize(10)
        self.pathLineEdit.setFont(font)
        self.pathLineEdit.setObjectName("pathLineEdit")

        # variables
        self.configuration = {}
        self.camConfig = {}
        self.image = []
        self.calib_image = []
        self.imageDirectory = ''
        self.fileName = ''
        self.calibration = False
        self._filterControls = [self.filt0CheckBox, self.filt1CheckBox,
                                self.filt2CheckBox, self.filt3CheckBox,
                                self.filt4CheckBox]
        self._exposureControls = [self.exp0LineEdit, self.exp1LineEdit,
                                  self.exp2LineEdit, self.exp3LineEdit,
                                  self.exp4LineEdit]
        self.timestamp = '{:%Y-%m-%d_%H-%M-%S}'.format(datetime.datetime.now())

        self._sender = None

        # get configuration
        self.filestr = 'system_config.ini'
        if not os.path.exists(self.filestr):
            self.filestr = QFileDialog.getOpenFileName(self, 'Open configuration file',
                                                       'c:\\', "config files (*.ini)")[0]
            if self.filestr == '':
                exit(1)

        try:
            with open(self.filestr) as file:
                for line in file.readlines():
                    if line.startswith('#'):
                        continue
                    conf = line.strip('\n').split('=')
                    self.configuration.update({conf[0]: conf[1]})
        except:
            print('Error during reading of configuration')
            exit(1)

        self.activeFilter = collections.OrderedDict()

        # set the filter widgets properties
        try:
            for idx, control in enumerate(self._filterControls):
                control.setText(str(idx) + ': ' + self.configuration['filter{}'.format(idx)])
                control.stateChanged.connect(self.updateFilter)
                self.activeFilter.update({idx: control.checkState()})
        except KeyError:
            print('Configuration file is missing filter specifications. Check 5 filters present.')
            exit(1)

        # set exposure settings
        # exposure settings only numerical
        validator = QIntValidator(1, 10000)
        try:
            for idx, control in enumerate(self._exposureControls):
                control.setValidator(validator)
                value = int(self.configuration['exposure{}'.format(idx)])
                control.setText(str(value))
                control.editingFinished.connect(self.updateConfig)
                self.camConfig.update({idx: {'ExposureTime': value * 1000}})
        except KeyError:
            print('Configuration file is missing exposure specifications. Check 5 exposures present')
            exit(1)
        except ValueError:
            print('Configuration file containing faulty specs. Check exposures numerical only.')
            exit(1)

        # populate the tag table
        # tags except 'comment' will only accept valid filename characters
        self.tags = ['User', 'Trial', 'Box ID', 'Cotton ID', 'Comment']
        self.trialTagTable.setRowCount(5)
        self.trialTagTable.setColumnCount(1)
        self.trialTagTable.setHorizontalHeaderLabels(['Tag'])
        self.trialTagTable.setVerticalHeaderLabels(self.tags)
        validator = QRegExpValidator(QRegExp(r"^[\w\- ]{1,254}$"))
        for idx in range(4):
            item = QLineEdit()
            item.setValidator(validator)
            self.trialTagTable.setCellWidget(idx, 0, item)
        item = QLineEdit()
        self.trialTagTable.setCellWidget(4, 0, item)

        # the sub thread for the live came process
        self.th = Thread(self)

        # connect slots
        self.quitButton.clicked.connect(self.quitApp)
        self.captureLiveButton.clicked.connect(self.startLiveCapture)
        self.captureFrameButton.clicked.connect(self.captureFrame)
        self.storeConfigButton.clicked.connect(self.storeConfig)
        self.pathLineEdit.clicked.connect(self.setImageDirectory)
        self.updateConfigSucces.connect(self.updateConfigState)
        self.th.updateConfigSuccess.connect(self.updateConfigSucces)

        # instantiate Hardware # TODO capture missing hardware errors
        self.cam = None
        self.filt = image_acquisition.FilterController(True)

    @pyqtSlot()
    def updateConfig(self):
        """Slot that triggers the cam configuration update with the new exposure settings.

        """
        # keep sender in internal memory for later reference of last sender
        self._sender = self.sender()
        value = self.sender().text()
        sender = self.sender().objectName()[3]

        print(sender, value)

        if self.th.running:
            self.th.updateConfig.emit(value, sender)
            self.camConfig.update({int(sender): {'ExposureTime': int(value) * 1000}})
        else:
            if self.cam is not None:
                self.cam.updateCameraConfig({int(sender): {'ExposureTime': int(value) * 1000}})
                self.camConfig.update({int(sender): {'ExposureTime': int(value) * 1000}})
                self.updateConfigSucces.emit(True)

    @pyqtSlot(bool)
    def updateConfigState(self, success):
        """Slot that updates the configuration dictionary if the camera settings have been
        updated successfully or rejects the changes if not.

        Parameters
        ----------
        success : bool
            The status of the cam settings update.

        """

        value = self._sender.text()
        sender = self._sender.objectName()[3]
        if success:
            self.configuration.update({'exposure' + sender: value})
            # triggers recapture of calibration frame
            self.calibration = False
        else:
            self._sender.setText(self.configuration['exposure' + sender])


    @pyqtSlot()
    def storeConfig(self):
        """Slot to write the current configuration into the file.

        """

        with open(self.filestr, 'w') as file:
            for key, value in self.configuration.items():
                file.write('{}={}\n'.format(key, value))


    @pyqtSlot(int)
    def updateFilter(self, filterState):
        """Slot to keep track of the selected filters by storing the values in an array

        Parameters
        ----------
        filterState : int
            0: not checked
            2: checked
        """
        sender = int(self.sender().objectName()[4])
        self.activeFilter.update({sender: filterState})

    @pyqtSlot()
    def captureFrame(self): #TODO implement convenient file naming
        """Slot to capture a single frame consisting of n images according
        to the number of n of selected filters
        """
        # open camera interface if not already opened
        if self.cam is None:
            self.cam = image_acquisition.ImageAcquisition(True)
            self.cam.updateCameraConfig(self.camConfig)

         # check if images should be saved
        if self.saveCheckBox.checkState() == 2:
            if self.imageDirectory == '':
                self.setImageDirectory()
            # get the tags for the filename
            user = self.trialTagTable.cellWidget(0, 0).text()
            trial = self.trialTagTable.cellWidget(1, 0).text()
            origin = self.trialTagTable.cellWidget(2, 0).text()
            label = self.trialTagTable.cellWidget(3, 0).text()
            comment = self.trialTagTable.cellWidget(4, 0).text()
            if user == '' or origin == '' or label == '':
                QMessageBox.warning(self, 'Missing Tags',
                                    'Please enter "User", "Cotton Origin" and "Cotton ID" and repeat.')
                return

       # check if a calibration image needs to be taken
        if not self.calibration:
            self.calib_image = []
            QMessageBox.warning(self, 'Calibration required',
                                'Remove samples and place a white sheet of paper in the sample area. Press OK to continue.')
            for idx in range(5):
                self.cam.setPosition(idx)
                self.filt.setPosition(idx)
                img = self.cam.capture()
                self.calib_image.append(img)
            QMessageBox.warning(self, 'Calibration finished', 'Replace paper with cotton samples. Press OK to continue.')

        # grab images
        self.image = []
        for idx in range(5):
            if self.activeFilter[idx] == 2:
                self.cam.setPosition(idx)
                self.filt.setPosition(idx)
                img = self.cam.capture()
                print(np.sum(img))
                img_view = img.copy()
                cv2.normalize(img, img_view, 0, 255, cv2.NORM_MINMAX)
                img_view = img_view.astype('uint8')
                convertToQtFormat = QImage(img_view, img_view.shape[1],
                                           img_view.shape[0], QImage.Format_Grayscale8)
                p = convertToQtFormat.scaled(816, 683, Qt.QtCore.Qt.KeepAspectRatio)
                self.setImage(p)
            else:
                img = []
            self.image.append(img)

        # save if selected
        if self.saveCheckBox.checkState() == 2:
            self.fileName = '{}_{user}_{trial}_{origin}'.format(self.timestamp, user=user, trial=trial,
                                                                origin=origin)
            print(self.fileName)

            # open / create hdf5 file and add data
            fileName = ''.join([self.imageDirectory, '/', self.fileName, '.hdf5'])
            if not os.path.exists(fileName):
                file = h5py.File(fileName, 'a')
                config = file.create_group('global')
                samples = file.create_group('samples')
                calibration = file.create_group('calibration')
                config.create_dataset('Trial', (1,), data=trial)
                for k, v in self.configuration.items():
                    config.create_dataset(k, (1,), data=v)
                for key, value in self.cam.paramSets.items():
                    params = config.create_group(self.configuration['filter{}'.format(key)])
                    for k, v in value.items():
                        params.create_dataset(k, (1,), data=v)
                self.calibration = False
            else:
                file = h5py.File(fileName, 'a')
                config = file['/global']
                samples = file['/samples']
                calibration = file['/calibration']
            timestamp = '{:%Y-%m-%d_%H-%M-%S}'.format(datetime.datetime.now())
            sample = samples.create_group(timestamp)
            sample.create_dataset('Cotton origin', (1,), data=origin)
            sample.create_dataset('Cotton ID', (1,), data=label)
            sample.create_dataset('Comment', (1,), data=comment)
            if not self.calibration:
                calib = calibration.create_group(timestamp)
                for idx in range(5):
                    calib.create_dataset('calibration_' + self.configuration['filter{}'.format(idx)],
                                         data=self.calib_image[idx], compression="gzip")
                self.calibration = True
            for idx in range(5):
                sample.create_dataset(self.configuration['filter{}'.format(idx)], data=self.image[idx],
                                      compression="gzip")
            file.close()

    @pyqtSlot()
    def setImageDirectory(self):
        """Slot to call QFileDialog to get a path to store the image files

        """
        directory = QFileDialog()
        directory.setFileMode(QFileDialog.Directory)
        directory.setOption(QFileDialog.ShowDirsOnly, True)
        path = directory.getExistingDirectory(self, 'Select Image location')

        if path == '':
            return
        self.imageDirectory = path
        self.pathLineEdit.setText(path)
        self.pathLineEdit.setCursorPosition(0)


    @pyqtSlot(QImage)
    def setImage(self, image):
        """Slot that changes the shown image by setting the pixmap.

        Parameters
        ----------
        image : QImage
            The image.

        """

        self.imageView.setPixmap(QPixmap.fromImage(image))

    @pyqtSlot()
    def startLiveCapture(self):
        """Slot for starting the live video capture

        """
        camWheelPosition = 0
        control = 0
        for key, value in self.activeFilter.items():
            if value > 0:
                control += 1
                camWheelPosition = key


        if control != 1:
            QMessageBox.warning(self, 'Wrong filter selection',
                                'Only 1 filter allowed for live view!!')
            return

        # close cam frame interface and open live interface
        if self.cam is not None:
            self.cam.close()
            self.cam = None
        cam = image_acquisition.LiveImage(None, True, self.camConfig)
        self.filt.setPosition(camWheelPosition)

        # initiliaze separate thread and start
        self.th.changePixmap.connect(self.setImage)
        self.th.cam = cam
        self.th.camWheelPosition = camWheelPosition
        self.th.start()

        self.captureLiveButton.clicked.disconnect(self.startLiveCapture)
        self.captureLiveButton.clicked.connect(self.stopLiveCapture)

        # some screen updates
        self.captureLiveButton.setText('Stop Capture')
        self.setInteractionState(False, camWheelPosition)

    pyqtSlot()
    def stopLiveCapture(self):
        """Slot for stopping the live video capture

        """
        self.th.stop()
        self.th.cam.close()

        self.captureLiveButton.clicked.disconnect(self.stopLiveCapture)
        self.captureLiveButton.clicked.connect(self.startLiveCapture)

        # some screen updates
        self.captureLiveButton.setText('Live View with current filter')
        self.setInteractionState(True)


    @pyqtSlot()
    def quitApp(self):
        """Close the current application.

        """
        if self.cam is not None:
            self.cam.close()
        self.close()
        QCoreApplication.quit()


    def setInteractionState(self, state, camWheelPosition=0):
        """Enable/Disable elements on the GUI to block interaction.

        Parameters
        ----------
        state : bool
            State of the possibility to interact with the element
        camWheelPosition: int, optional
            Index of the active camera setting.

        """

        self.captureFrameButton.setEnabled(state)
        for control in self._filterControls:
            control.setEnabled(state)
        for idx, control in enumerate(self._exposureControls):
            if (state == False) and (idx == camWheelPosition):
                continue
            control.setEnabled(state)
        self.quitButton.setEnabled(state)
        self.storeConfigButton.setEnabled(state)
        self.saveCheckBox.setEnabled(state)
        self.pathLineEdit.setEnabled(state)


if __name__ == '__main__':
    if not os.path.exists('USDAcontrol.ui'):
        print('No ui-file found')
        exit()
    app = QApplication(sys.argv)
    ex = App()
    ex.show()
    sys.exit(app.exec_())

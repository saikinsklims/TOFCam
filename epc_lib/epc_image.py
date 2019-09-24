#-------------------------------------------------------------------------------
# Name:        epc_image
# Purpose:     Python class for project-independent stuff related to image
#              acquisition
# Version:     3.0
# Created:     28.01.2019
# Authors:     sho
# Copyright:   (c) ESPROS Photonics AG, 2016
#-------------------------------------------------------------------------------


# Official Libraries
import sys
import numpy as np
import socket
import struct

class epc_image:

    def __init__(self, epc_server):
        self._server = epc_server

    def getDCSs(self):
        s = socket.create_connection((self._server.IP, self._server.port))
        command = 'getDCSSorted\n'
        s.send(command.encode())

        imageDataVector = bytearray()
        remaining = self._imageSizeBytesAllDCSs
        while remaining > 0:
            chunk = s.recv(remaining)       # Get available data.
            imageDataVector.extend(chunk)   # Add to already stored data.
            remaining -= len(chunk)

        s.close()
        return self._imageVectorToArray(imageDataVector, self._numberOfImageDataFrame)

    def getDistAmpl(self):
        s = socket.create_connection((self._server.IP, self._server.port))
        command='getDistanceAndAmplitudeSorted\n'
        s.send(command.encode())

        imageDataVector = bytearray()
        remaining = (self._imageSizeBytes) * 2
        while remaining > 0:
            chunk = s.recv(remaining)       # Get available data.
            imageDataVector.extend(chunk)   # Add to already stored data.
            remaining -= len(chunk)

        s.close()
        return self._imageVectorToArray(imageDataVector, 2)

    def getDist(self):
        s = socket.create_connection((self._server.IP, self._server.port))
        command='getDistanceSorted\n'
        s.send(command.encode())

        imageDataVector = bytearray()
        remaining = (self._imageSizeBytes) * 2
        while remaining > 0:
            chunk = s.recv(remaining)       # Get available data.
            imageDataVector.extend(chunk)   # Add to already stored data.
            remaining -= len(chunk)

        s.close()
        return self._imageVectorToArray(imageDataVector, 1)

    def getAmpl(self):
        s = socket.create_connection((self._server.IP, self._server.port))
        command='getAmplitudeSorted\n'
        s.send(command.encode())

        imageDataVector = bytearray()
        remaining = (self._imageSizeBytes) * 2
        while remaining > 0:
            chunk = s.recv(remaining)       # Get available data.
            imageDataVector.extend(chunk)   # Add to already stored data.
            remaining -= len(chunk)

        s.close()
        return self._imageVectorToArray(imageDataVector, 1)

    def getTemperature(self):
        s = socket.create_connection((self._server.IP, self._server.port))
        command='getTemperature\n'
        s.send(command.encode())
        tempVector = bytearray()
        chunk = s.recv(2)       # Get available data.
        tempVector=chunk
        s.close()

        unpackedString = 'H' * (int(tempVector.__len__()/2)) # signed short (16bit)
        tempData16bit = list(struct.unpack('<'+unpackedString, tempVector)) # little endian

        return tempData16bit


    def setNumberOfRecordedColumns(self, NbrMeasCols):
        self._numberOfColumns  = NbrMeasCols

    def getNumberOfRecordedColumns(self):
        return self._numberOfColumns

    def setNumberOfRecordedRows(self, NbrMeasRows):
        self._numberOfRows  = NbrMeasRows

    def getNumberOfRecordedRows(self):
        return self._numberOfRows

    def setNumberOfRecordedImageDataFrames(self, NbrMeasDataFrame):
        self._numberOfImageDataFrame = NbrMeasDataFrame

    def getNumberOfRecordedImageDataFrames(self):
        return self._numberOfImageDataFrame

    def updateNbrRecordedBytes(self):
        self._imageSizeBytes        = self._numberOfRows * self._numberOfColumns * 2
        self._imageSizeBytesAllDCSs = self._numberOfImageDataFrame * self._imageSizeBytes

    def _imageVectorToArray(self, imageDataVector, numberOfElements):
        imageDataVector = bytes(imageDataVector)

        unpackedString = 'H' * (int(imageDataVector.__len__() / 2))  # signed short (16bit)

        imageData16bit = list(struct.unpack('<' + unpackedString, imageDataVector))  # little endian

        # Store data directly as numpy array:
        imageData = np.transpose(np.reshape(np.array(imageData16bit, dtype='uint16'), (numberOfElements, self._numberOfRows, self._numberOfColumns)), [2, 1, 0])

        return imageData

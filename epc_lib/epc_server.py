#-------------------------------------------------------------------------------
# Name:        epc_server
# Purpose:     Python class to communicate with a server running on a DME660.
# Version:     1.0
# Created:     16.06.2016
# Last change: 16.08.2016
# Authors:     twi, mle
# Copyright:   (c) ESPROS Photonics AG, 2016
#-------------------------------------------------------------------------------


# Official Libraries
import sys
import socket
import array
import numpy as np


class epc_server:

    def __init__(self, serverIP="192.168.7.2", serverPort=50660):
        self.IP   = serverIP
        self.port = serverPort
        self._N_REGS = 0x100

        self.checkConnection()


    def checkConnection(self):
        try:
            s = socket.create_connection((self.IP, self.port), 1)
            s.close()
        except:
            sys.exit("ERROR: Connection could not be established. Please check IP and network connection and make sure that a suitable server is running.")
        print("INFO: Connection to server successfully established.")

    def sendCommand(self, command):
        s = socket.create_connection((self.IP, self.port))
        command += "\n"  # support for C++ server
        s.send(command.encode())
        resp = s.recv(100)
        resp_len = len(resp)
        ints = array.array('h', resp)
        s.close()
        if len(ints) == 1 and ints[0] == -1:
            sys.exit("ERROR: Server command '" + command[:-1] + "' failed.")
        else:
            print('INFO: Server command \'' + command[:-1] + '\' executed.')
        return ints


    def sendCommandSequence(self, commandList):
        """
            Sends a list of commands to the server: input the lines as list of lists,
            if more than one command per function execution is needed.
            Example: sendCommandSequence([['w xx yy','w xx yy','w xx yy'], /
                                          ['w xx yy','w xx yy','w xx yy'], /
                                          ['w xx yy','w xx yy','w xx yy'], /])
        """
        for command in commandList:
            self.sendCommand(command)


    def i2c(self, arguments):
        arguments += "\n"  # support for C++ server
        if arguments[0]=='w':
            s = socket.create_connection((self.IP, self.port))
            s.send(arguments)
            s.recv(4) # wait for response from server
            s.close()
            return 0
        elif arguments[0]=='r':
            s = socket.create_connection((self.IP, self.port))
            s.send(arguments)
            try:
                n_bytes = 4*int(arguments.split(' ')[2])
            except:
                n_bytes = 4
            bytes = array.array('h',s.recv(n_bytes))
            s.close()
            return bytes
        else:
            sys.exit("ERROR: Invalid i2c command '" + arguments + "'")
        return -1


    def getRegisterDump(self):
        s = socket.create_connection((self.IP, self.port))
        s.send("dumpAllRegisters\n")
        registerDump = np.frombuffer(s.recv(self._N_REGS*2), dtype="h") # 256 * 2 bytes = 512 bytes
        s.close()
        return registerDump


    def readRegister(self, address):
        """
            Returns register value from the register addressed by 'address'.
        """
        return self.i2c("r %02X" %(address))[0]


    def writeRegister(self, address, value):
        """
            Writes register value 'value' to the register addressed by 'address'.
        """
        self.i2c("w %02X %02X" %(address, value))

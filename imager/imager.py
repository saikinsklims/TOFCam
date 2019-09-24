# -*- coding: utf-8 -*-

def imagerInit(server, imgDev):
	
	fullROI				 =   1   #1 for full ROI image  on a epc660
	enableCompensations	 =   1   #1 for compensated DATA
	setModulation			=	1	#1 for enabling own modulation configuration (not the GUI configurations)
	
	if fullROI:
		server.sendCommand('w 11 fa')
		icType=server.sendCommand('r 12')
	if (icType[0]==2):
		numberOfRows		= 240
		numberOfColumns	 = 320
		numberOf3DimageDataframe = 2	 # 1 Distance + 1 Amplitued = 2 images
	elif (icType[0]==4):
		numberOfRows		= 60
		numberOfColumns	 = 160
		numberOf3DimageDataframe = 2	 # 1 Distance + 1 Amplitued = 2 images
	else:
		numberOfColumns	 = int(input('Enter number of cols:'))
		numberOfRows	 = int(input('Enter number of rows:'))
	
	#####################################################################################
	# initialize var																	#
	#####################################################################################
	
	#imageData3D = np.empty([numberOfColumns, numberOfRows, numberOf3DimageDataframe], dtype='uint16')
		
	imgDev.setNumberOfRecordedColumns(numberOfColumns)
	imgDev.setNumberOfRecordedRows(numberOfRows)
	imgDev.setNumberOfRecordedImageDataFrames(numberOf3DimageDataframe);
	imgDev.updateNbrRecordedBytes()
	
	#####################################################################################
	# measurement																	   #
	#####################################################################################
	
	server.sendCommand('enableSaturation 1')		# 1 = enable saturation	 flag value = 65400
	server.sendCommand('enableAdcOverflow 1')	   # 1 = enable ADC overflow   flag value = 65500
		
	#set modulation frequency and integration times if needed	
	if setModulation:							  	#set mod frequency and integration times if needed
		#set mod frequency
		modFreq={'20_24MHz':0,'10_12MHz':1}
		setModFreq = '20_24MHz'
		server.sendCommand('setModulationFrequency '+str(modFreq[setModFreq]))
		#set integration times		
		server.sendCommand('setIntegrationTime2D 600')	 # t_int in us
		server.sendCommand('setIntegrationTime3D 600')	  # t_int in us
		
	#enable compensations if needed		
	if enableCompensations:
		server.sendCommand('correctTemperature 1')	  # 1 = enable temperature correction
		server.sendCommand('correctAmbientLight 1')	 # 1 = enable ambient light correction
		server.sendCommand('correctDRNU 2')			 # 2 = enable DRNU correction
	else:
		server.sendCommand('correctTemperature 0')	  # 1 = enable temperature correction
		server.sendCommand('correctAmbientLight 0')	 # 1 = enable ambient light correction
		server.sendCommand('correctDRNU 0')			 # 1 = enable DRNU correction
	
	server.sendCommand('loadConfig 1')				  # loadConfig 1 = TOF mode (3D imaging)
	
	server.sendCommand('startVideo')	 				# increases the fps, but only usable if you don't record the temperature, too


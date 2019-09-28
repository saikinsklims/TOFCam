import cv2
import numpy as np
from epc_lib import epc_server, epc_image
import h5py


def displayImage(img, autoScale=True, colorMap=True):
	# Rotate image
	dimg = cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)

	# Determine pixel masks for invalid measurements
	low_amplitude = np.where(dimg == 65300)
	saturation = np.where(dimg == 65400)
	adc_overflow = np.where(dimg == 65500)

	if autoScale:
		# Set pixels to invalid to make sure values do not screw with min/max calculations
		dimg = dimg.astype(np.float)
		dimg[low_amplitude] = np.NaN
		dimg[saturation] = np.NaN
		dimg[adc_overflow] = np.NaN

		# Scale uint16 values to range of values actually in the image
		minpx = np.nanmin(dimg)
		maxpx = np.nanmax(dimg)
		dimg = (255.0 * (dimg - minpx)) / (maxpx - minpx)
		dimg = dimg.astype(np.uint8)

	else:
		# dimg type is 16bits, but only 12 bits are used
		# we extract only the upper 8 bits
		dimg = (dimg >> 4).astype(np.uint8)

	# Convert grayscale image to color image
	dimg = cv2.cvtColor(dimg, cv2.COLOR_GRAY2RGB)

	# Instead of grayscale image use colormap to color image
	if colorMap:
		dimg = cv2.applyColorMap(dimg, cv2.COLORMAP_JET)

	# Apply pixel masks by coloring invalid measurements
	dimg[low_amplitude] = [255, 0, 0] # Blue
	dimg[saturation] = [0, 255, 0] # Green
	dimg[adc_overflow] = [0, 0, 255] # Red

	# Upscale image to make it visible on high res screens
	scale = 5.0
	width = int(dimg.shape[1] * scale)
	height = int(dimg.shape[0] * scale)
	dimg = cv2.resize(dimg, (width, height), interpolation = cv2.INTER_CUBIC)

	return dimg



### Main Objects
server = epc_server('192.168.7.2') # USB connection
#server  =  epc_server('192.168.1.80') # Ethernet connection

#mode = 'distamp'
mode = 'dcs'

saveNumImages = 200




image_epcDev   =  epc_image(server)

#####################################################################################
# Parameters																		#
#####################################################################################
fullROI				 =   1   #1 for full ROI image  on a epc660
enableCompensations	 =   1   #1 for compensated DATA
setModulation			=	1	#1 for enabling own modulation configuration (not the GUI configurations)

if fullROI:
	server.sendCommand('w 11 fa')
	icType=server.sendCommand('r 12')
	if (icType[0]==2):
		numberOfRows		= 240
		numberOfColumns	 = 320
		numberOf3DimageDataframe = 4	 # 4 DCS
	elif (icType[0]==4):
		numberOfRows		= 60
		numberOfColumns	 = 160
		numberOf3DimageDataframe = 4	 # 4 DCS
else:
	numberOfColumns	 = int(input('Enter number of cols:'))
	numberOfRows		= int(input('Enter number of rows:'))

#####################################################################################
# initialize var																	#
#####################################################################################

#imageData3D = np.empty([numberOfColumns, numberOfRows, numberOf3DimageDataframe], dtype='uint16')

image_epcDev.setNumberOfRecordedColumns(numberOfColumns)
image_epcDev.setNumberOfRecordedRows(numberOfRows)
image_epcDev.setNumberOfRecordedImageDataFrames(numberOf3DimageDataframe);
image_epcDev.updateNbrRecordedBytes()

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
	server.sendCommand('setIntegrationTime2D 300')	 # t_int in us
	server.sendCommand('setIntegrationTime3D 300')	  # t_int in us

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

#server.sendCommand('startVideo')	 				# increases the fps, but only usable if you don't record the temperature, too



cv2.namedWindow('ESPROS ToF Cam')

enableSaveImages = False

while True:
	if mode == 'distamp':
		imageData3D = image_epcDev.getDistAmpl()

		ampImg  = imageData3D[:,:,1]
		distImg = imageData3D[:,:,0]

		dispAmpImg = displayImage(ampImg, autoScale=False, colorMap=False)
		dispDistImg = displayImage(distImg, autoScale=True, colorMap=True)
		dispImg = np.hstack((dispAmpImg, dispDistImg))

		cv2.imshow('ESPROS ToF Cam', dispImg)

	elif mode == 'dcs':
		imageData3D = image_epcDev.getDCSs()
		images = []
		for i in range(imageData3D.shape[2]):
			dcs_i = imageData3D[:,:,i]
			dispDCS_i = displayImage(dcs_i, autoScale=False, colorMap=False)
			cv2.putText(dispDCS_i, f'DCS{i}', (20, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), lineType=cv2.LINE_AA)
			images.append(dispDCS_i)

		dispImg = np.vstack((np.hstack((images[0], images[2])),np.hstack((images[1], images[3]))))
		cv2.imshow('ESPROS ToF Cam', dispImg)
	else:
		raise Exception(f'Unknown mode {mode}')

	key = cv2.waitKey(10)
	if key == 27 or key == ord('q'):
		break
	elif key == ord('s'):
		print('Aquisition started ...')
		enableSaveImages = True
		# * is the so-called "unpack" operator in Python!
		savedImageData = np.zeros((*(imageData3D.shape), saveNumImages))
		numImagesSaved = 0

	if enableSaveImages:
		savedImageData[:,:,:,numImagesSaved] = imageData3D
		numImagesSaved += 1
		print(f'Saved {numImagesSaved}/{saveNumImages}.')
		if numImagesSaved == saveNumImages:
			enableSaveImages = False
			print('Saving file ...')
			h5f = h5py.File('data.h5', 'w')
			h5f.create_dataset(mode, data=savedImageData, dtype='uint16')
			h5f.close()
			print('Saving file done.')

cv2.destroyAllWindows()

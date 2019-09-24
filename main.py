# -*- coding: utf-8 -*-
import cv2
import numpy as np
from epc_lib import epc_server, epc_image
from imgProc import imgProcScale
from imager import imager

### Main Objects
#epc_server('192.168.7.2') # USB connection
server  		=  epc_server('192.168.1.80') # Ethernet connection
image_epcDev   	=  epc_image(server)

#####################################################################################
# Parameters																		#
#####################################################################################

# init whole imager
imager.imagerInit(server, image_epcDev)


while True:

	# get image and amplitude
	imageData3D = image_epcDev.getDistAmpl()
	imgAmp  = imageData3D[:,:,1]
	imgDist = imageData3D[:,:,0]
	# convert the images and scale them if needed	
	imgAmpScale = imgProcScale.convertImage(imgAmp, autoScale=False, colorMap=False)
	imgDistScale = imgProcScale.convertImage(imgDist, autoScale=True, colorMap=True)
	
	

	
	
	
	
	
	
	# display images
	cv2.imshow('Distance', imgDistScale)
	cv2.imshow('Amplitude', imgAmpScale)
	
	key = cv2.waitKey(1)
	if key == 27 or key == ord('q'):
		break

cv2.destroyAllWindows()


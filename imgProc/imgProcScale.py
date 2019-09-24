import cv2
import numpy as np


def convertImage(img, autoScale=True, colorMap=True):
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
	scale = 4.0
	width = int(dimg.shape[1] * scale)
	height = int(dimg.shape[0] * scale)
	dimg = cv2.resize(dimg, (width, height), interpolation = cv2.INTER_CUBIC)

	return dimg


def convertImageGray(img):
	# Rotate image
	dimg = cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)
	# Upscale image to make it visible on high res screens
	scale = 4.0
	width = int(dimg.shape[1] * scale)
	height = int(dimg.shape[0] * scale)
	dimg = cv2.resize(dimg, (width, height), interpolation = cv2.INTER_CUBIC)

	return dimg
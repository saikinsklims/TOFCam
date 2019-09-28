import cv2
import numpy as np


def scale_image_rgb(img, autoScale=True, colorMap=True):
    """
    Converts the given distance image into an RGB-image and rescales
    the image for better visibility

    Parameters
    ----------
    img : numpy array
        The distance image.
    autoScale : bool, optional
        Rescale the value range to fit uint8. The default is True.
    colorMap : bool, optional
        Use a colormap instead of a gray scale. The default is True.

    Returns
    -------
    dimg : numpy array
        The converted and rescaled image.

    """
	# Rotate image
    dimg = cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)
	
	# Determine pixel masks for invalid measurements
    low_amplitude = np.where(dimg == 65300)
    saturation = np.where(dimg == 65400)
    adc_overflow = np.where(dimg == 65500)
	
    if autoScale:
        # Set pixels to invalid to make sure values do not screw with min/max calculations
        g = dimg.astype(np.float)
        g[low_amplitude] = np.NaN
        g[saturation] = np.NaN
        g[adc_overflow] = np.NaN
		
		# Scale uint16 values to range of values actually in the image
        minpx = np.nanmin(dimg)
        maxpx = np.nanmax(dimg)
        g = (255.0 * (dimg - minpx)) / (maxpx - minpx)
	
    dimg = dimg.astype(np.uint8)
	
	# Convert grayscale image to color image
    dimg = cv2.cvtColor(dimg, cv2.COLOR_GRAY2RGB)
	
	# Instead of grayscale image use colormap to color image
    if colorMap:
        g = cv2.applyColorMap(dimg, cv2.COLORMAP_JET)
	
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


def scale_image_gray(img):
    """
     Rescales the given distance image for for better visibility   

    Parameters
    ----------
    img : numpy array
        The distance image.

    Returns
    -------
    dimg : numpy array
        The rescaled image.

    """
	# Rotate image
    dimg = cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)
	# Upscale image to make it visible on high res screens
    scale = 4.0
    width = int(dimg.shape[1] * scale)
    height = int(dimg.shape[0] * scale)
    dimg = cv2.resize(dimg, (width, height), interpolation = cv2.INTER_CUBIC)

    return dimg

def calc_image_cog(img, auto_thresh, threshold=None):
    """
    Calculate the image moments after background suppression.

    Parameters
    ----------
    img : numpy array
        The distance image.
    auto_thresh: bool
        Use auto background calculation.      
    threshold: float
        The threshold distance that should mark the background

    Returns
    -------
    moments : list
        The image moments.

    """

    if not auto_thresh and not threshold:
        print("""Auto treshold used as no threshold defined. To avoid this
              define threshold.""")

    # threshold is 1/10th of image max
    thresh = img.max() * 0.1
    if threshold and not auto_thresh:
        thresh = threshold

    # segmentation of image into foreground and background
    img_bin = (img > thresh).astype(np.uint8)

    # get moments and calculated the center of gravity
    moments = cv2.moments(img_bin)
    cog_x = moments['m10'] / (moments['m00'] + 1e-5)  # avoid zero by a ~0
    cog_y = moments['m01'] / (moments['m00'] + 1e-5)

    return (cog_x, cog_y)
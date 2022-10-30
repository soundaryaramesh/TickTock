# all the imports go here
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import find_peaks, peak_prominences


# peak detection
def prominence_based(y, h, d, p, w):
	peaks, properties = find_peaks(y, height=h, distance=d, \
		prominence=p, wlen=w)
	return peaks, properties

def compute_peak_prominences(y, peaks, wlen=None):
	prominences = peak_prominences(y, peaks, wlen)[0]
	return prominences

def amplitude_based(y, h, d):
	peaks, properties = find_peaks(y, height=h, distance=d)
	return peaks, properties

# moving average-based filter
def moving_avg_filter(y, k):
	h = np.ones(2*k+1)/(2*k)
	h[k] = 0
	print(str(h))
	fy_ = np.convolve(y,h,'same')
	fy = y- fy_
	fy[fy<0] = 0
	return fy_, fy
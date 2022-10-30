# all the imports go here
import sys
import numpy as np
import matplotlib.pyplot as plt
from configparser import ConfigParser
import detection_steps as det
import time
import detect

# add parent dir to python path
sys.path.append('../')

import peak_detection as pd
import clk_freq_detection as cfd 
import utils

def plot_detection_steps(fp, fund_freq, height, parser, sdr, n=100, is_plt=True):
	# allowable distance b/w predicted and correct freq
	dist_freq = parser.getint(sdr, 'allowable_dist_freq')
	if is_plt:
		fig, (ax1, ax2, ax3) = plt.subplots(3)
	# saves True if the predicted clock freq is correct, and is the only one
	correct_clk_pred = np.zeros(n, dtype=bool)
	# saves the number of clk freq predicted (ideally should be 1)
	n_clk_pred = np.zeros(n, dtype=int)
	c = 0 # read trials sequentially from the start, until n
	start_t = time.time()
	while c < n: 
		# 1. Read data
		try:
			raw_data = np.load(fp)
		except:
			# print("End of File")
			break
		
		data, sloc, ploc, pval, clklist, _, _, _ = \
			detect.detect_per_trial(raw_data, height, parser, sdr)
		print("Clock freq: ",clklist, " predicted!")
		#if clklist.size >= 1 and \
		if clklist.size == 1 and \
			utils.if_acceptable_dist(clklist, fund_freq, dist_freq):
			correct_clk_pred[c] = True

		n_clk_pred[c] = clklist.size

		if is_plt:# and clklist.size != 0:#and \
			#utils.if_acceptable_dist(clklist,3072, dist_freq):
			plt.suptitle('Device: ' + device + ' C value: '+str(c))
			#det.plot_clk_freq(ax1, ax2, data, sloc, ploc, pval, fund_freq, parser, sdr)
			plot_spectrum(ax1, raw_data, parser, sdr, "Raw Data")
			plot_spectrum(ax2, data, parser, sdr, "After Mean Removal")
			plot_spectrum(ax3, data, parser, sdr, "Peak Detection", ploc, pval, label = True)
			plt.show(block=False)

			tmp = input("Enter a character (x to exit): ")
			c = c+1
			if tmp == 'x':
				break

			ax1.clear()
			ax2.clear()
			ax3.clear()
		else:
			c = c+1
	end_t = time.time()
	print("Compute time: ",end_t - start_t)
	# print("Total no of trials: ",c)
	return correct_clk_pred, n_clk_pred, c

""" plots raw data, mean removal, peak detection """
def plot_spectrum(ax, data, parser, sdr, title, peak_loc = None, peak_val = None, label = False):
	# read from config
	n_sweeps = parser.getint(sdr, 'n_sweeps')
	sampl_per_sweep = parser.getint(sdr, 'sampl_per_sweep')
	freq_per_sweep = parser.getint(sdr, 'freq_per_sweep')
	is_alias = parser.getboolean(sdr, 'is_alias')

	N = n_sweeps * sampl_per_sweep
	fs = n_sweeps * freq_per_sweep

	if is_alias:
		nyq_freq = parser.getint(sdr, 'nyquist_freq')

	freq_offset, _ = utils.compute_freq_range(parser, sdr)
	xf = freq_offset + np.linspace(0, fs, N, False)

	ax.plot(xf/1e6, data)
	ax.set_title(title)
	ax.set(ylabel = 'Magnitude (dB)')
	if label:
		ax.set(xlabel = 'Frequency (MHz)')
	if ~np.all(peak_loc == None):
		ax.plot(peak_loc/1e6, peak_val,"x")
	ax.set_xlim([(freq_offset)/1e6, (freq_offset+fs)/1e6])

if __name__ == '__main__':
	# read binary log fft data from file
	if len(sys.argv) != 6:
		print("Format python3 ", sys.argv[0], " <sdr> <file-name> <freq (kHz)> <threshold> <print?>")
		sys.exit(1)

	# init param
	max_trials = 1000 # no. trials considered

	sdr = sys.argv[1]	
	device = sys.argv[2]
	fund_freq = float(sys.argv[3]) # in kHz
	height = float(sys.argv[4]) # in dBm
	if sys.argv[5] == "True" or sys.argv[5] == "true":
		print_bool = True
	else:
		print_bool = False

	# init parser
	parser = ConfigParser()
	parser.read("../config.ini")
	
	# read binary log fft data from file
	print("Device: ", device)
	folder_name = parser.get(sdr, 'folder')
	fname = folder_name + device + '.bin'
	fp = open(fname, "rb")

	bool_clk, n_clk_pred, n_trials = plot_detection_steps(fp, fund_freq, height, parser, sdr, max_trials, print_bool)
	print("No. of correct predictions: ", np.sum(bool_clk), "out of ",n_trials)
	# print(n_clk_pred)
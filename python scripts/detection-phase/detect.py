# all the imports go here
import sys
import numpy as np
import matplotlib.pyplot as plt
from configparser import ConfigParser
import detection_steps as det
import time

# add parent dir to python path
sys.path.append('../')

import peak_detection as pd
import clk_freq_detection as cfd 
import utils

def detect_freq_and_compute_performance(fp, fund_freq, height, parser, sdr, max_trials, print_bool=False):
	# get dist freq
	dist_freq = parser.getfloat(sdr, 'allowable_dist_freq')

	clk_pred_dict, n_clk_pred, n_trials = detect(fp, height, parser, sdr, max_trials, print_bool)
	bool_clk = compute_performance(clk_pred_dict, n_trials, fund_freq, dist_freq)
	perc_success = np.around(np.sum(bool_clk)/float(n_trials) * 100, decimals=2)
	print("No. of correct predictions: ", np.sum(bool_clk), "out of ",n_trials, " (", perc_success,"% )")
	return bool_clk, n_clk_pred, n_trials

def compute_performance(clk_pred_dict, n, fund_freq, dist_freq):
	# saves True if the predicted clock freq is correct, and is the only one
	correct_clk_pred = np.zeros(n, dtype=bool)
	for i in range(n):
		clk_pred_i = clk_pred_dict[i]
		if clk_pred_i.size == 1 and \
			utils.if_acceptable_dist(clk_pred_i, fund_freq, dist_freq):
			correct_clk_pred[i] = True
	return correct_clk_pred

def detect(fp, height, parser, sdr, n=3000, is_plt=True):
	# dictionary of all predictions
	clk_pred_dict = {}
	# saves the number of clk freq predicted (ideally should be 1)
	n_clk_pred = np.zeros(n, dtype=int)

	if is_plt:
		fig, (ax1, ax2) = plt.subplots(2)
	
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
			detect_per_trial(raw_data, height, parser, sdr)
		clk_pred_dict[c] = clklist
		n_clk_pred[c] = clklist.size

		dist_freq = parser.getint(sdr, "allowable_dist_freq")
		#clklist.size != 0 and 
		if is_plt and clklist.size >= 1 and \
			utils.if_acceptable_dist(clklist, fund_freq, dist_freq):
			plt.suptitle('Device: ' + device + ' C value: '+ str(c))
			det.plot_clk_freq(ax1, ax2, data, sloc, ploc, pval, fund_freq[0], parser, sdr)
			fig.canvas.draw()
			plt.draw()
			plt.show(block=False)

			tmp = input("Enter a character (x to exit): ")
			if tmp == 'x':
				break

			ax1.clear()
			ax2.clear()
		c = c+1
	end_t = time.time()
	# print("Compute time: ",end_t - start_t)
	# print("Total no of trials: ",c)
	return clk_pred_dict, n_clk_pred, c

def detect_per_trial(raw_data, height, parser, sdr):
	# read from config file
	sampl_per_sweep = parser.getint(sdr, 'sampl_per_sweep')
	is_alias = parser.getboolean(sdr, 'is_alias')
	if is_alias:
		nyq_freq = parser.getint(sdr, 'nyquist_freq')
	else:
		nyq_freq = 0

	""" 2. preprocessing: mean removal """
	# per-sweep or overall
	data = det.mean_offset_removal(raw_data, "per-sweep", sampl_per_sweep)
	""" 3. peak detection : amplitude-based """
	# return sample loc (sloc), freq loc (ploc), amplitude value at loc (pval)
	sloc, ploc, pval = det.detect_peak(data, height, parser, sdr)
	# print("Peaks: ",np.around(ploc/1e3))
	""" 4. clk freq prediction : amplitude-based """
	# returns clock freq list, corresp. score list and all detected harmonics 
	pr_clklist, pr_scrlist, pr_hmoniclist, pr_hamplist = cfd.detect_clk_freqs(ploc, pval, nyq_freq, parser, sdr)
	""" 5. aliasing correction """
	# considering the case where all the frequencies may be aliased
	if pr_clklist.size == 0 and nyq_freq != 0:
		pr_clklist, pr_scrlist, pr_hmoniclist, pr_hamplist = det.correct_for_aliasing(ploc, pval, nyq_freq, parser, sdr)
	
	if pr_clklist.size > 1:
		# print("Clk list (before pruning): ", pr_clklist)
		# print("Harmonic peaks: ", pr_hmoniclist)
		clklist, scrlist, hmoniclist, hamplist = det.perform_freq_pruning(pr_clklist, \
				pr_scrlist, pr_hmoniclist, pr_hamplist, parser, sdr)
	else:
		clklist = pr_clklist
		scrlist = pr_scrlist
		hmoniclist = pr_hmoniclist
		hamplist = pr_hamplist
		
	# # the only freq present is the required clock freq => good location
	print_clk = False
	if print_clk:
		if clklist.size >= 1:
			print("Clk list (after pruning): ", clklist)
		# # 	# print("C: ", c, " Good location found!")
			print("Score: ", scrlist)
			# print("Harmonic peaks: ", hmoniclist)
		# # 	#print("No. of excess peaks: ", len(ploc)-scrlist[0])
		else:
			print("Clock frequency NOT present")
	return data, sloc, ploc, pval, clklist, scrlist, hmoniclist, hamplist

if __name__ == '__main__':
	# read binary log fft data from file
	if len(sys.argv) != 7:
		print("Format python3 detect.py <sdr> <file-name> <freq (kHz)> <threshold> <oe-hmonic (yes/no)>  <print? (true/false)>")
		sys.exit(1)

	# init param
	max_trials = 650 # no. trials considered

	sdr = sys.argv[1]	
	device = sys.argv[2]
	fund_freq = [int(f) for f in sys.argv[3].split(',')] # in kHz
	height = float(sys.argv[4]) # in dBm
	oe_hmonic = sys.argv[5]
	print_bool = [True if sys.argv[6] == "True" or sys.argv[6] == "true" else False][0]

	# init parser
	parser = ConfigParser()
	parser.read("../config.ini")
	parser.set(sdr, "only_odd_harmonic", oe_hmonic)
	

	# read binary log fft data from file
	print("Device: ", device)
	folder_name = parser.get(sdr, 'folder')
	fname = folder_name + device + '.bin'
	fp = open(fname, "rb")

	detect_freq_and_compute_performance(fp, fund_freq, height, parser, sdr, max_trials, print_bool)

	

# all the imports go here
import sys
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import find_peaks
from configparser import ConfigParser
import os

# add parent dir to python path
sys.path.append('../')
sys.path.append('../detection-phase/')

import peak_detection as pd
import clk_freq_detection as cfd
import calibration_utils as cutils
import utils
import detect as det

def combine_clk_freq_across_readings(parser, sdr, device):
	# init parser
	cname = 'calibrate'

	# read binary log fft data from file
	print("File: ", device)
	folder_name = parser.get(sdr, 'folder')
	fname = os.path.join(folder_name, device + '.bin')
	fp = open(fname, "rb")

	# freq limits for mic clock
	min_mic_freq = parser.getint(sdr, 'min_mic_freq')
	max_mic_freq = parser.getint(sdr, 'max_mic_freq')

	# # peak detection param
	height = parser.getfloat(sdr, 'height') #in dB
	dist_freq = parser.getfloat(sdr, 'allowable_dist_freq')
	# score
	score = parser.getint(sdr, 'score')

	# # clock frequency list
	max_num_freq = parser.getint(cname, 'max_num_freq')
	freq_list = np.zeros(max_num_freq, dtype=np.int32)
	count_list = np.zeros(max_num_freq, dtype=np.int32)
	oe_hcount_list = np.zeros([max_num_freq,2], dtype=np.int32) #odd-even
	ampl_list = {}
	min_ampl_list = np.zeros(max_num_freq, dtype=np.float32)
	is_diff_sdr = parser.getboolean(cname, 'diff_sdr')

	loc = 0
	max_lim = False
	c = 0 # reading no. being processed
	while True: 
		try:
			raw_data = np.load(fp)
		except:
			# print("End of File")
			break

		_, _, _, _, clklist, scrlist, hmoniclist, hamplist = \
			det.detect_per_trial(raw_data, height, parser, sdr)
		n_freq = clklist.size
		if n_freq == 0:
			c += 1
			continue

		for i in range(n_freq):
			freq = clklist[i]
			# ignore non-mic freq
			if freq < min_mic_freq or freq > max_mic_freq:
				continue
			if np.any(freq_list == freq):
				idx = np.where(freq_list == freq)[0][0]
			else:
				idx = loc
				freq_list[idx] = freq
				ampl_list[idx] = []
				loc += 1 
			
			count_list[idx] = count_list[idx] + 1
			oe_hcount_list[idx] = oe_hcount_list[idx] + \
				cutils.compute_odd_even_hmonic(freq, hmoniclist[i], parser, sdr)

			k_ampl = cutils.compute_k_max_ampl(freq, hamplist[i], parser, sdr)
			ampl_list[idx].append(k_ampl)
	
			if loc >= max_num_freq:
				print("Max num freq exceeded: ", max_num_freq)
				print("Returning only top ",max_num_freq, " freq")
				max_lim = True
				break
		if max_lim:
			break
		c += 1

	freq_list = freq_list[:loc]
	count_list = count_list[:loc]
	oe_hcount_list = oe_hcount_list[:loc]

	# print("Before merging...","Total runs: ", c)
	# print("Clock list: ", freq_list,"Count list: ", count_list, "Amplitude list: ", ampl_list, "Harmonic Count: ", oe_hcount_list)

	freq_list, count_list, oe_hcount_list, ampl_list = \
		cutils.merge_closeby_freq(freq_list, count_list, oe_hcount_list, ampl_list, dist_freq)
	freq_list, count_list, oe_hcount_list, ampl_list = \
		cutils.sort_by_count(freq_list, count_list, oe_hcount_list, ampl_list)

	return freq_list, count_list, oe_hcount_list, ampl_list

if __name__ == "__main__":
	# read command-line inputs
	if len(sys.argv) != 3:
		print("Format python3 calibrate.py <sdr> <file-name>")
		sys.exit(1)

	sdr = sys.argv[1]
	file_name = sys.argv[2]

	parser = ConfigParser()
	parser.read("../config.ini")
	# set calibration flag to yes
	parser.set(sdr, 'config_mode', 'yes')	
	# freq_list, count_list, top_k_ampl, min_ampl = calibrate_clock_freq(sdr, file_name)
	freq_list, count_list, oe_hcount_list, ampl_list = \
		combine_clk_freq_across_readings(parser, sdr, file_name)

	# print("After merging and sorting...")
	print("Number of entries: ",np.size(freq_list))
	print("Clock list: ", freq_list)
	print("Count list: ", count_list)
	print("Odd-even harmonic list: ",oe_hcount_list)
	print("Ampl list: ", ampl_list)

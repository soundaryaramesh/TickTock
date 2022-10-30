import sys
import os
import numpy as np
import copy
from configparser import ConfigParser
from calibrate import combine_clk_freq_across_readings
# add parent dir to python path
sys.path.append('../')
import utils

def mic_freq_id(mic_file, nomic_file, parser, sdr):
	cname = 'calibrate'
	height = parser.getfloat(sdr, 'height')
	min_count = parser.getint(cname, 'min_count')
	max_count = parser.getint(cname, 'max_count')
	del_height = parser.getfloat(cname, 'del_height')
	least_possible_height = parser.getfloat(cname, 'least_possible_height')
	max_possible_height = parser.getfloat(cname, 'max_possible_height')

	is_up, is_down = False, False
	while True:
		chosen_mic_clk, chosen_mic_count, chosen_oe_bool, chosen_mic_ampl = \
			compare_readings(mic_file, nomic_file, height, parser, sdr)
		if chosen_mic_count < min_count:
			height = height - del_height
			is_down = True
			if is_up:
				print("As the height has already gone up...quitting")
				final_mic_clk, final_mic_count, final_oe_bool, final_mic_ampl = \
					prev_mic_clk, prev_mic_count, prev_oe_bool, prev_mic_ampl
				break
			if height < least_possible_height:
				print("As the height is the min height...quitting")
				final_mic_clk, final_mic_count, final_oe_bool, final_mic_ampl = \
					chosen_mic_clk, chosen_mic_count, chosen_oe_bool, chosen_mic_ampl
				break
		elif chosen_mic_count > max_count:
			print("Saving values at height: ", height)
			prev_mic_clk, prev_mic_count, prev_oe_bool, prev_mic_ampl = \
				chosen_mic_clk, chosen_mic_count, chosen_oe_bool, chosen_mic_ampl
			height = height + del_height
			is_up = True
			if height > max_possible_height or is_down:
				print("As the height is the max height / has already gone down...quitting")
				final_mic_clk, final_mic_count, final_oe_bool, final_mic_ampl = \
					chosen_mic_clk, chosen_mic_count, chosen_oe_bool, chosen_mic_ampl
				break
		else:
			final_mic_clk, final_mic_count, final_oe_bool, final_mic_ampl = \
					chosen_mic_clk, chosen_mic_count, chosen_oe_bool, chosen_mic_ampl
			break
	print("="*10,"FINAL VALUES","="*10)
	print("Mic clock freq(s): ", final_mic_clk)
	print("Count: ",final_mic_count)
	print("Mean Amplitude: ", final_mic_ampl)
	print("only_odd_harmonic = ",final_oe_bool)
	return final_mic_clk, final_mic_count, final_oe_bool, final_mic_ampl

# compare the clock frequencies present in readings with mic, and without mic 
def compare_readings(mic_file, nomic_file, height, main_parser, sdr):
	# required to prevent height from being overwritten
	parser = copy.deepcopy(main_parser)
	parser.set(sdr, 'height', str(height))
	diff_sdr = parser.getboolean('calibrate', 'diff_sdr')

	dist_freq = parser.getfloat(sdr, 'allowable_dist_freq')
	req_oe_frac = parser.getfloat('calibrate', 'oe_frac')
	
	print("Height: ",height)
	# mic ON
	mic_clk, mic_count, mic_oe_hmonic, mic_ampl = combine_clk_freq_across_readings(parser, sdr, mic_file)
	# mic OFF
	nomic_clk, nomic_count, nomic_oe_hmonic, nomic_ampl = combine_clk_freq_across_readings(parser, sdr, nomic_file)

	print("Initial mic list: ", mic_clk, " count: ", mic_count)
	# print("Amplitude: ", mic_ampl)
	# print("O/E harmonic: ",mic_oe_hmonic)
	print("Initial no-mic list: ", nomic_clk, " count: ", nomic_count)
	n_mic = np.size(mic_clk)
	n_no_mic = np.size(nomic_clk)

	if n_mic == 0: # not possible to be here - according to prev. logic
		print("No mic clock frequency detected")
		return np.array([]), 0, False, 0
	elif n_no_mic == 0:
		best_idx = np.argmax(mic_count)
	else:
		# sort in descending order of count
		sort_idx = np.argsort(mic_count)[::-1]
		best_idx = -1
		for i in range(n_mic):
			mic_clk_i = mic_clk[sort_idx[i]]
			# check if the mic_clk_i is within close distance of any of the non-mic frequencies
			bool_idx = utils.if_acceptable_dist(mic_clk_i, nomic_clk, dist_freq)
			if not(bool_idx):
				best_idx = sort_idx[i]
				break
	if best_idx == -1:
		print("No unique mic clock frequency detected")
		return np.array([]), 0, False, 0

	chosen_mic_clk = mic_clk[best_idx]
	chosen_mic_count = mic_count[best_idx]
	chosen_oe_hmonic = mic_oe_hmonic[best_idx,0]/np.sum(mic_oe_hmonic[best_idx])
	chosen_oe_bool = chosen_oe_hmonic > req_oe_frac
	chosen_mic_ampl = mic_ampl[best_idx]
	# CHECK the code for diff SDR
	if not(diff_sdr):
		chosen_mean_ampl = np.mean(chosen_mic_ampl)
	else:
		print("Diff SDR: Using min")
		chosen_mean_ampl = np.min(chosen_mic_ampl)

	print("Most likely mic clock freq(s): ", chosen_mic_clk)
	print("Count: ",chosen_mic_count)
	print("Min Amplitude: ", chosen_mean_ampl)
	print("Odd-even harmonic (%): ",np.around(chosen_oe_hmonic*100, decimals=2))
	print("only_odd_harmonic = ",chosen_oe_bool)

	return chosen_mic_clk, chosen_mic_count, chosen_oe_bool, chosen_mean_ampl

if __name__ == "__main__":
	# read command-line inputs
	if len(sys.argv) != 4:
		print("Format python3", sys.argv[0],  "<sdr> <file-name-with-mic> <file-name-without-mic>")
		sys.exit(1)

	sdr = sys.argv[1]
	mic_file = sys.argv[2]
	nomic_file = sys.argv[3]
	parser = ConfigParser()
	parser.read("../config.ini")
	# set calibration flag to yes
	parser.set(sdr, 'config_mode', 'yes')	
	
	_,_,_,_= mic_freq_id(mic_file, nomic_file, parser, sdr)
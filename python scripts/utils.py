import numpy as np
import json

def compute_aliased_frequencies(freq_list, nyq_freq):
	twice_nyq_freq = 2*nyq_freq
	capped_freq_list = freq_list - twice_nyq_freq*np.floor(freq_list/twice_nyq_freq)
	bool_list = capped_freq_list <= nyq_freq
	aliased_freq_list = bool_list * capped_freq_list + \
		~bool_list * (twice_nyq_freq - capped_freq_list)
	return aliased_freq_list

def compute_freq_range(parser, sdr):
	start_cfreq = parser.getint(sdr, 'starting_center_freq')
	freq_per_sweep = parser.getint(sdr, 'freq_per_sweep')
	n_sweeps = parser.getint(sdr, 'n_sweeps')
	bin_select = parser.get(sdr, 'bin_select')
	upconverted = parser.getint(sdr, 'upconverted')
	if bin_select == 'both_sided':
		start_freq = start_cfreq - freq_per_sweep/2 - upconverted
	else:
		bin_skip = parser.getint(sdr, 'bin_skip')
		sampl_per_sweep = parser.getint(sdr, 'sampl_per_sweep')
		start_freq = start_cfreq + \
			int(bin_skip*freq_per_sweep/sampl_per_sweep) - upconverted
	end_freq = start_freq + n_sweeps * freq_per_sweep
	return start_freq, end_freq

def update_req_score(fund_freq, parser, sdr):
	_, end_freq = compute_freq_range(parser, sdr)
	score = parser.getint(sdr, 'score')
	min_score = parser.getint(sdr, 'min_score')
	# keep a pessimistic estimate - esp. useful during calibration
	config_mode = parser.getboolean(sdr, 'config_mode')
	if config_mode:
		only_odd_harmonic = True
	else:
		only_odd_harmonic = parser.getboolean(sdr, 'only_odd_harmonic')
	max_possible_hmonic = np.floor(end_freq/fund_freq)
	if only_odd_harmonic:
		n_possible_hmonics = np.ceil(max_possible_hmonic/2)
	else:
		n_possible_hmonics = max_possible_hmonic
	# assert(n_possible_hmonics > 1)
	upd_score = int(np.minimum(score, n_possible_hmonics-1))
	if upd_score < min_score:
            upd_score = min_score
	# if upd_score <= 2:
	# 	print("Req score <= 2!!")
	return upd_score

def compute_all_center_frequencies(start_f, jump_f, nf):
	all_f = start_f + jump_f * np.arange(nf)
	return all_f

def compute_aliased_peaks(fpeaks, nyq_freq):
	assert(np.all(fpeaks) < nyq_freq)
	alias_fpeaks = 2*nyq_freq - fpeaks
	# all_fpeaks = np.concatenate((fpeaks, alias_fpeaks), axis=None)
	return alias_fpeaks

""" Returns true if distance is acceptable, else false"""
def if_acceptable_dist(pred_val, exp_val, dist):
	pred_val = np.array(pred_val)
	exp_val = np.array(exp_val)
	if exp_val.size == 0 or pred_val.size == 0:
		return False
	if exp_val.size == 1 or pred_val.size == 1:
		return np.any(np.abs(pred_val-exp_val) <= dist)
	else:
		# if any of the predicted is similar to any of the expected
		n_exp = exp_val.size
		for i in range(n_exp):
			is_close = np.any(np.abs(pred_val - exp_val[i]) <= dist)
			if is_close == True:
				return True
		return False

def obtain_fundamental(k_harmonic_freq, k, unit='mhz'):
	k = np.float(k)
	# frequency (in Hz) cannot be fractional in kHz
	fund_freq = np.around(k_harmonic_freq/k, decimals = -3)
	if unit == "mhz":	
		return fund_freq
	if unit == "khz":
		fund_freq_khz = int(fund_freq/1e3)
		return fund_freq_khz
	print("Error in freq unit!")
	sys.exit()


# save config data as JSON
def save_config_logs(fname, parser, section):
	dict_data = dict(parser[section])
	fp = open(fname, "a")
	json.dump(dict_data, fp)
	fp.close()


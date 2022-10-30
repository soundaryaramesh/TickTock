""" Detect presence / absence of clock frequency """
import numpy as np
import utils

def detect_clk_freqs(peak_loc, req_score, harmonics, \
	min_freq=1.0e6, max_freq=4.8e6, err_freq=1e-2, nyq_freq=0):
	k_harmonics = [1, 3, 5]
	
	# print("Peak loc: ", peak_loc)

	peak_loc = np.array(peak_loc, dtype='float32')
	n_peak_loc = len(peak_loc)

	clk_freq_list = np.array([],dtype=np.float32)
	score_list = np.array([], dtype=np.float32)
	all_hpeaks = {}
	
	is_clk = False

	# print("peak_loc: ", peak_loc)
	if n_peak_loc < req_score:
		return clk_freq_list, score_list, all_hpeaks

	for k in k_harmonics:
		# print("k: ", k)
		# check for first odd harmonic (fh) and other odd harmonics
		is_kh =  (peak_loc >= k*min_freq) & (peak_loc <= k*max_freq)
		# print("is_kh: ", is_kh)
		candidate_kh_list = peak_loc[is_kh]
		if len(candidate_kh_list) > 0:
			n_kh = len(candidate_kh_list)
			for j in range(n_kh):
				cand_k_harmonic_freq = candidate_kh_list[j]
				# print("cand ", k, "harmonic freq: ", cand_k_harmonic_freq)
				cand_freq_khz, score, hpeaks_khz = detect_if_fundamental(peak_loc, \
					cand_k_harmonic_freq, k, req_score, err_freq, harmonics, nyq_freq)
				# if cand_freq_khz != 0:
					# print("New clock freq: ", cand_freq_khz, "kHz")
				if cand_freq_khz != 0 and cand_freq_khz not in clk_freq_list: 					
					is_clk = True
					# update kHz values
					clk_freq_list = np.append(clk_freq_list, cand_freq_khz)
					score_list = np.append(score_list, score)
					all_hpeaks[len(score_list)-1] = hpeaks_khz
					# print("clk_freq_list: ", clk_freq_list)
	
	return clk_freq_list, score_list, all_hpeaks

def detect_if_fundamental(peak_loc, harmonic_peak, hval, req_score, errf, oddh, nyqf):
	fund_peak_khz = 0
	score = 0 # initial score
	hpeaks_khz = 0
	# print("Harmonic peak: ",harmonic_peak, "Hval: ",hval)
	fund_peak = utils.obtain_fundamental(harmonic_peak, hval)
	
	score, fund_peak, hidx_monitor = detect_harmonics(fund_peak, peak_loc, \
		errf, oddh, False)

	# if score > req_score:
	# 	print("Peaks so far: ", peak_loc[hidx_monitor])
	
	if nyqf == 0:
		overall_score = score
		hpeaks = peak_loc[hidx_monitor]
	else:
		not_choosen_peak_loc = peak_loc[~hidx_monitor]
		alias_peak_loc = utils.compute_aliased_peaks(not_choosen_peak_loc, nyqf)

		alias_score, _, alias_hidx_monitor = detect_harmonics(fund_peak, alias_peak_loc, \
			errf, oddh, True)

		# if score > req_score:
		# 	print("Not chosen peaks: ", not_choosen_peak_loc)
		# 	print("Aliased peaks: ",alias_peak_loc)
		# 	print("Alias peaks: ", alias_peak_loc[alias_hidx_monitor])

		overall_score = score + alias_score
		hpeaks = np.concatenate((peak_loc[hidx_monitor],\
		alias_peak_loc[alias_hidx_monitor]), axis=None)

	if overall_score >= req_score:
		fund_peak_khz = int(fund_peak/1e3)
		hpeaks_khz = np.around(hpeaks/1e3, decimals=0)
	
	return fund_peak_khz, overall_score, hpeaks_khz


def detect_harmonics(fund_peak, peak_loc, errf, oddh, is_alias):
	peak_div = np.around(peak_loc / fund_peak, decimals=3)
	# print("Initial peak div: ", peak_div)

	nh = len(oddh)
	hidx_monitor = np.zeros(len(peak_loc), dtype=np.bool)
	score = 0

	for i in range(nh):
		kh = oddh[i]
		# if kh < hval: 
		# 	continue

		if np.all(peak_div < (kh-errf)):
			break
		# print("Odd harmonic no: "+str(kh))
		err_list = np.abs(peak_div-kh)
		hidx = np.argmin(err_list)
		# is_harmonic = np.where(err_list < errf)
		# if is_harmonic[0].size != 0:
		if err_list[hidx] < errf:
			# when a harmonic is identified, add it to a list
			hidx_monitor[hidx] = True

			# hidx = is_harmonic[0][0]
			score = score + 1

			# i.e., if this is the first time this condition is satisfied
			# to prevent repeat detection of same freq as different freq
			if score == 1 and ~is_alias: 
				# print("k val: ", kh)
				# print("Peak loc first time: ", peak_loc[hidx])
				fund_peak = utils.obtain_fundamental(peak_loc[hidx], kh)
				# print("Fund peak: ", fund_peak)
				peak_div = np.around(peak_loc / fund_peak, decimals=3)
				# print("Peak div: ", peak_div)

	return score, fund_peak, hidx_monitor
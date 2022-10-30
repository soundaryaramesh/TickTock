import numpy as np
import utils

""" returns likely clock frequencies present based on the detected peaks """
""" OUTPUT : clk_freq_list ==> (N,), nhmonic_list ==> (N,),
	hpeaks_dict ==> no. of keys = N, value = variable size list,
	hampl_dict ==> no. of keys = N, value = variable size list"""
def detect_clk_freqs(peak_loc, peak_val, nyq_freq, parser, sdr):
	# init output lists / dicts
	clk_freq_list = np.array([],dtype=np.float32) # clock freq
	nhmonic_list = np.array([], dtype=np.float32) # no. of harmonics
	hpeaks_dict = {} # freq of harmonics (khz)
	hampl_dict = {} # ampl of harmonics

	min_req_score = parser.getint(sdr, 'min_score')
	if np.size(peak_loc) < min_req_score:
		# return empty lists
		return clk_freq_list, nhmonic_list, hpeaks_dict, hampl_dict

	min_freq = parser.getint(sdr, 'min_freq')
	max_freq = parser.getint(sdr, 'max_freq')
	
	min_dist = parser.getint(sdr,'allowable_dist_freq')
	max_first_hmonic = parser.getint(sdr, 'max_first_harmonic') 

	only_odd_hmonic = parser.getboolean(sdr, 'only_odd_harmonic')
	if only_odd_hmonic:
		k_hmonics = np.arange(1,max_first_hmonic+1,2)
	else:
		k_hmonics = np.arange(1,max_first_hmonic+1)

	# list storing eliminated clock freq to speedup detection
	bad_candidates = np.array([])

	for k in k_hmonics:
		# find peaks that can be kth harmonic of a clock freq
		is_kh =  (peak_loc >= k*min_freq) & (peak_loc <= k*max_freq)
		candidate_kh_list = peak_loc[is_kh]
		n_kh = candidate_kh_list.size
		if candidate_kh_list.size == 0:
			continue
		for j in range(n_kh):
			cand_k_hmonic = candidate_kh_list[j]
			cand_freq_mhz = utils.obtain_fundamental(cand_k_hmonic, k, 'mhz')
			cand_freq_khz = utils.obtain_fundamental(cand_k_hmonic, k, 'khz')
			
			# the freq is in the list of bad candidates or chosen clk list
			if utils.if_acceptable_dist(cand_freq_khz, bad_candidates, min_dist) \
				or utils.if_acceptable_dist(cand_freq_khz, clk_freq_list, min_dist):
				continue 
			# all returned freq in khz	
			is_clk, nhmonics, hpeaks, hampl = detect_if_clk(peak_loc, peak_val, \
				cand_freq_mhz, parser, sdr, nyq_freq)
			if is_clk: 					
				clk_freq_list = np.append(clk_freq_list, cand_freq_khz)
				nhmonic_list = np.append(nhmonic_list, nhmonics)
				hpeaks_dict[len(nhmonic_list)-1] = hpeaks
				hampl_dict[len(nhmonic_list)-1] = hampl
			else:
				bad_candidates = np.append(bad_candidates, cand_freq_khz)
	return clk_freq_list, nhmonic_list, hpeaks_dict, hampl_dict

""" returns score, harmonics (freq+ampl) for a given clock freq (i.e., fund_peak) """
def detect_if_clk(peak_loc, peak_val, fund_peak, parser, sdr, nyqf):
	err_frac = parser.getfloat(sdr, 'err_frac')
	only_odd_hmonic = parser.getboolean(sdr, 'only_odd_harmonic')

	# init output params
	is_clk = False
	hpeaks_khz = -1

	req_score = utils.update_req_score(fund_peak, parser, sdr)
	score, hmonic_bool = detect_harmonics(fund_peak, peak_loc, peak_val, \
		err_frac, only_odd_hmonic)
	if nyqf == 0:
		overall_score = score
		hpeaks = peak_loc[hmonic_bool]
		hampl = peak_val[hmonic_bool]
	else:
		not_chosen_peak_loc = peak_loc[~hmonic_bool]
		not_chosen_peak_val = peak_val[~hmonic_bool]
		alias_peak_loc = utils.compute_aliased_peaks(not_chosen_peak_loc, nyqf)

		alias_score, alias_hmonic_bool = detect_harmonics(fund_peak, alias_peak_loc, \
			not_chosen_peak_val, err_frac, only_odd_hmonic)

		overall_score = score + alias_score
		hpeaks = np.concatenate((peak_loc[hmonic_bool],\
			not_chosen_peak_loc[alias_hmonic_bool]), axis=None)
		hampl = np.concatenate((peak_val[hmonic_bool], \
			not_chosen_peak_val[alias_hmonic_bool]), axis=None)

	if overall_score >= req_score:
		is_clk = True
		hpeaks_khz = np.rint(hpeaks/1e3)
	return is_clk, overall_score, hpeaks_khz, hampl

""" returns score, harmonic idxs for a given clock freq """
def detect_harmonics(fund_peak, peak_loc, peak_val, err_frac, is_odd):
	peak_div = peak_loc / fund_peak
	hmonic_num = np.rint(peak_div)
	comp_err_div = np.around(np.abs(peak_div-hmonic_num), decimals=4)

	# location of potential harmonics
	hidx_bool = comp_err_div < err_frac
	hidxs = np.where(hidx_bool)[0]
	
	nh = hidxs.size
	if nh == 0:
		return 0, hidx_bool

	detected_hmonics = np.array([])
	for i in range(nh):
		hidx = hidxs[i]
		kh = hmonic_num[hidx] # which harmonic
		if np.any(detected_hmonics == kh) or \
			(is_odd and kh%2==0): # only odd harmonics and only one peak per hmonic
			hidx_bool[hidx] = False
			continue
		else:
		 	detected_hmonics = np.append(detected_hmonics, kh)
	# number of potential harmonics
	score = np.sum(hidx_bool)
	return score, hidx_bool


import numpy as np
import sys
sys.path.append('../')
import utils

def merge_closeby_freq(freq_list, count_list, oe_hcount_list, ampl_list, dist_freq):
	if freq_list.size == 0:
		return np.array([]),[],{},[]
	# merge close-by frequencies into one
	upd_freq_list, group_idxs = group_elements(freq_list, count_list, dist_freq)
	upd_count_list = merge_by_groups(count_list, group_idxs, 'arr', 'sum')
	upd_oe_hcount_list = merge_by_groups(oe_hcount_list, group_idxs, 'arr', 'sum')
	upd_ampl_list = merge_by_groups(ampl_list, group_idxs, 'dict', 'append')
	return upd_freq_list, upd_count_list, upd_oe_hcount_list, upd_ampl_list

def sort_by_count(freq_list, count_list, oe_hcount_list, ampl_list):
	if freq_list.size == 0:
		return np.array([]),[],{},[]
	# final sort based on count-score
	arg_count_sort = np.argsort(count_list)[::-1]
	sort_freq_list = sort_by_idx(freq_list, arg_count_sort)
	sort_count_list = sort_by_idx(count_list, arg_count_sort)
	sort_oe_hcount_list = sort_by_idx(oe_hcount_list, arg_count_sort)
	sort_ampl_list = sort_by_idx(ampl_list, arg_count_sort, 'dict')
	return sort_freq_list, sort_count_list, sort_oe_hcount_list, sort_ampl_list

""" Identify groups of frequencies that are close in distance """
def group_elements(data, count, dist):
	arg_sort_data = np.argsort(data)
	sort_data = data[arg_sort_data]
	group_idxs = []

	n = data.size

	diff_list = np.diff(sort_data) > dist
	true_pos = np.where(diff_list)[0]
	sidx = np.append(0, true_pos+1)
	eidx = np.append(true_pos+1, n)

	n_groups = sidx.size
	group_leaders = np.zeros(n_groups)

	for i in range(n_groups):
		s = sidx[i]; e = eidx[i]
		if (e-s) > 1:
			# choose the element with max count as the leader
			group_val = np.array(sort_data[s:e])
			orig_idx = arg_sort_data[s:e]
			group_cnt = np.array(count[orig_idx])
			max_arg = np.argmax(group_cnt)

			group_leaders[i] = group_val[max_arg]
			group_idxs.append(orig_idx)
		else:
			group_leaders[i] = sort_data[s]
			group_idxs.append(np.array(arg_sort_data[s]))
	return group_leaders, group_idxs


def merge_by_groups(data, group_idxs, dtype='arr', merge_method='sum'):
	if dtype == 'arr':
		assert(merge_method == 'sum' or merge_method == 'min')
		merged_data = merge_lists_by_groups(data, group_idxs, merge_method)
	elif dtype == 'dict':
		assert(merge_method == 'append')
		merged_data = merge_dicts_by_groups(data, group_idxs, merge_method)
	else:
		print("ERROR: Invalid dtype")
		sys.exit(1)
	return merged_data


def merge_lists_by_groups(data, group_idxs, merge_method='sum'):
	n_groups = len(group_idxs)
	if data.size == data.shape[0]: # 1-D list
		merged_data = np.zeros(n_groups, dtype=data.dtype)
		dim2 = False
	else: # 2-D array
		n_col = data.shape[1]
		merged_data = np.zeros((n_groups, n_col), dtype=data.dtype)
		dim2 = True
	for i in range(n_groups):
		gidx = group_idxs[i]
		# print("gidx: ",gidx)
		if np.size(gidx) == 1: # single element
			merged_data[i] = data[gidx]
		else: # more than one element
			if merge_method == 'sum':
				data_i = np.sum(data[gidx], axis=0)
			elif merge_method == 'min':
				data_i = np.min(data[gidx], axis=0)
			else:
				print("Merge failed! Merge method incorrect!")
			# print("data_i: ",data_i)
			if dim2:
				assert data_i.size == n_col
			merged_data[i] = data_i 
	return merged_data

def merge_dicts_by_groups(data, group_idxs, merge_method='append'):
	assert(merge_method == "append")

	n_groups = len(group_idxs)
	merged_data = {}
	for i in range(n_groups):
		gidx = group_idxs[i]
		if np.size(gidx) == 1: # single element
			merged_data[i] = data[int(gidx)]
			continue
		merged_data[i] = []
		for j in gidx:
			merged_data[i].append(data[int(j)])
		# combine list of lists into one list
		merged_data[i] = sum(merged_data[i], [])
	return merged_data


def sort_by_idx(data, sort_idx, dtype='arr'):
	if dtype == 'arr':
		if data.size == data.shape[0]: # 1-D list
			return data[sort_idx]
		else:
			return data[sort_idx,:]
	elif dtype == 'dict':
		new_data = {}
		for i in range(sort_idx.size):
			new_data[i] = data[sort_idx[i]]
		return new_data

def compute_odd_even_hmonic(freq, hmonics_list, parser, sdr):
	max_err_frac = parser.getfloat(sdr, 'err_frac')
	err_margin = parser.getfloat(sdr, 'err_margin')
	is_alias = parser.getboolean(sdr, 'is_alias')
	n = hmonics_list.size
	assert n != 0
	freq_frac = np.around(hmonics_list/freq, decimals=4)
	hmonic_num = np.array(np.around(freq_frac),dtype=int)
	comp_err_frac = np.around(np.abs(freq_frac-hmonic_num), decimals=4)
	if is_alias:
		nyq_freq = parser.getint(sdr, 'nyquist_freq')/1e3 #kHz
		nyq_frac = 2*nyq_freq/freq
		al_freq_frac = np.around(nyq_frac-freq_frac, decimals=4)
		al_hmonic_num = np.array(np.around(al_freq_frac),dtype=int)
		al_comp_err_frac = np.around(np.abs(al_freq_frac-al_hmonic_num), decimals=4)
		al_idx = comp_err_frac > err_margin * max_err_frac 
		# update the hmonic num and comp_err_frac with the aliased counterparts
		hmonic_num[al_idx] = al_hmonic_num[al_idx]
		comp_err_frac[al_idx] = al_comp_err_frac[al_idx]
	# print(freq)
	# print(hmonics_list)
	# print(comp_err_frac)
	# print(comp_err_frac < (err_margin * max_err_frac))
	assert(np.all(comp_err_frac < (err_margin * max_err_frac)))
	mod_val = np.mod(hmonic_num,2)
	odd_count = np.sum(mod_val == 1)
	even_count = np.sum(mod_val == 0)
	assert odd_count + even_count == n
	return np.array([odd_count, even_count], dtype=int)
		

def compute_k_max_ampl(freq, data, parser, sdr):
	assert(parser.getboolean(sdr, "config_mode") == True)
	k = utils.update_req_score(freq*1e3, parser, sdr) # freq in kHz
	sort_data = np.sort(data)
	k_max_ampl = np.around(sort_data[-k], decimals=2)
	# print("Min ampl: ",k_max_ampl)
	return k_max_ampl
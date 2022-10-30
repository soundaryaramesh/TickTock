import numpy as np
""" given all the finally detected clock frequencies, remove redundant ones 
which could be harmonically / otherwise related to other detected frequencies """
def frequency_to_prune(clk_freq, clk_harmonics):
	n_clk = len(clk_freq)
	prune_idx = np.array([], dtype=np.int32)

	for i in range(n_clk):
		for j in range(i+1,n_clk):
			if (i in prune_idx) or (j in prune_idx):
				continue
			ni = clk_harmonics[i].size
			nj = clk_harmonics[j].size

			# both have same number of harmonics
			if ni == nj:
				diff_ij = np.setdiff1d(clk_harmonics[i], clk_harmonics[j])
				if diff_ij.size == 0:
					# retain the larger freq
					if clk_freq[i] > clk_freq[j]:
						prune_idx = np.append(prune_idx, j)
					else:
						prune_idx = np.append(prune_idx, i)
			# if ni is larger, see if j is a subset of i
			elif ni > nj:
				diff_ji = np.setdiff1d(clk_harmonics[j], clk_harmonics[i])
				if diff_ji.size == 0:
					prune_idx = np.append(prune_idx, j)
			# if nj is larger, see if i is a subset of j
			else:
				diff_ij = np.setdiff1d(clk_harmonics[i], clk_harmonics[j])					
				if diff_ij.size == 0:
					prune_idx = np.append(prune_idx, i)
	return prune_idx

def data_pruning(data, prune_idx, dtype):
	if dtype == 'list':
		l = data.shape[0]
		all_idx = np.ones(l, dtype=np.bool)
		all_idx[prune_idx] = False
		new_data = data[all_idx]
	elif dtype == 'dict':
		# new_data = data
		new_data = {}
		l = len(data)
		all_idx = np.ones(l, dtype=np.bool)
		all_idx[prune_idx] = False
		valid_idx = all_idx.nonzero()[0]
		for i in range(valid_idx.size):
			new_data[i] = data[valid_idx[i]]
	else:
		print("Error: Invalid type - ",dtype)
		new_data = []
	return new_data
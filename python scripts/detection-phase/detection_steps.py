import sys
import numpy as np
import time

# add parent dir to python path
sys.path.append('../')

import peak_detection as pd
import clk_freq_detection as cfd 
import utils
import prune_freq as pf

""" INPUT : y ==> (M,), type ==> overall/per-sweep, 
	n ==> samples per sweep (valid only for type = per-sweep)"""
""" OUTPUT : fil_y ==> (M, ) """
def mean_offset_removal(y, type="overall", n=None):
	if type == "overall":
		mean_y = np.mean(y)
		fil_y = y - mean_y
	elif type == "per-sweep":
		if np.gcd(y.size,n) != n:
			print("Did you enter the wrong sdr name?")
			sys.exit(1)
		reshape_y = y.reshape(-1,n)
		mean_per_sweep = np.mean(reshape_y, axis=1)
		mean_per_sample = np.repeat(mean_per_sweep, n)
		assert(mean_per_sample.size == y.size)
		fil_y = y - mean_per_sample
	else:
		print("Error in type: ",type)
		sys.exit(1)
	return fil_y

""" INPUT : data ==> (M,), height ==> amplitude threshold, 
	parser ==> Configparser, sdr ==> sdrplay/airspy/uhd/rtlsdr """
""" OUTPUT : sampl_loc ==> (m,), peak_loc ==> (m,), peak_val ==> (m,),
	m = no. of detected peaks """
def detect_peak(data, height, parser, sdr):
	dist = parser.getfloat(sdr, 'dist') #in samples
	freq_offset, _ = utils.compute_freq_range(parser, sdr)
	freq_per_sweep = parser.getint(sdr, 'freq_per_sweep')
	sampl_per_sweep = parser.getint(sdr, 'sampl_per_sweep')
	freq_res = float(freq_per_sweep/sampl_per_sweep)
	# peak detection
	sampl_loc, _ = pd.amplitude_based(data, height, dist)
	peak_loc = np.array(freq_offset + sampl_loc * freq_res, dtype='float32')
	peak_val = np.array(data[sampl_loc], dtype='float32')
	# print("Fpeaks are: ", peak_loc)
	return sampl_loc, peak_loc, peak_val

def correct_for_aliasing(ploc, pval, nyq_freq, parser, sdr):
	# assuming all peaks are aliased
	aliased_ploc = utils.compute_aliased_peaks(ploc, nyq_freq)
	#print("Aliased peaks are: ",aliased_ploc)
	al_clklist, al_scrlist, al_hmoniclist, al_amplist = cfd.detect_clk_freqs(aliased_ploc, pval, \
			0, parser, sdr)
	return al_clklist, al_scrlist, al_hmoniclist, al_amplist

def perform_freq_pruning(clklist, scrlist, hmoniclist, amplist, parser, sdr):
	# prune freq based on common harmonics
	prune_idx = pf.frequency_to_prune(clklist, hmoniclist)
	if prune_idx.size != 0:
		prune_clklist = pf.data_pruning(clklist, prune_idx, 'list')
		prune_scrlist = pf.data_pruning(scrlist, prune_idx, 'list')
		prune_hmoniclist = pf.data_pruning(hmoniclist, prune_idx, 'dict')
		prune_amplist = pf.data_pruning(amplist, prune_idx, 'dict')
		return prune_clklist, prune_scrlist, prune_hmoniclist, prune_amplist
	else:
		return clklist, scrlist, hmoniclist, amplist

def plot_clk_freq(ax1, ax2, data, sloc, ploc, pval, fund_freq, parser, sdr):
	# read from config
	n_sweeps = parser.getint(sdr, 'n_sweeps')
	sampl_per_sweep = parser.getint(sdr, 'sampl_per_sweep')
	freq_per_sweep = parser.getint(sdr, 'freq_per_sweep')
	is_alias = parser.getboolean(sdr, 'is_alias')

	N = n_sweeps * sampl_per_sweep
	fs = n_sweeps * freq_per_sweep

	only_odd_harmonic = parser.getboolean(sdr, 'only_odd_harmonic')
	max_harmonic = parser.getint(sdr, 'max_print_harmonic') # for printing purposes only
	if only_odd_harmonic:
		harmonics = np.arange(1,max_harmonic,2)
	else:
		harmonics = np.arange(1, max_harmonic,1)

	clk_freq = fund_freq * harmonics
	if is_alias:
		nyq_freq = parser.getint(sdr, 'nyquist_freq')
		clk_freq = utils.compute_aliased_frequencies(clk_freq, nyq_freq/1e3)

	freq_offset, _ = utils.compute_freq_range(parser, sdr)
	xf = freq_offset + np.linspace(0, fs, N, False)

	# calculate prominence of each peak
	prom = pd.compute_peak_prominences(data, sloc,100)
	# print(prom)
	countour_heights = pval - prom
	ax1.plot(xf/1e6, data)
	ax1.set_title("Expected peaks")
	ax1.set(xlabel = 'freq (MHz)', ylabel = 'magnitude (dB)')

	ax1.vlines(x=clk_freq/1e3, ymin=min(data), ymax=max(data), color="C1")
	ax1.set_xlim([(freq_offset)/1e6, (freq_offset+fs)/1e6])
	ax1.set_ylim([-40,60])

	ax2.plot(xf/1e6, data,linewidth=2)
	ax2.plot(ploc/1e6, pval,"o")
	ax2.vlines(x=ploc/1e6,ymin=countour_heights,ymax=pval)
	ax2.set_yticks(np.arange(-40,70,20))
	ax2.set_title("Obtained peaks")
	ax2.set_xlabel('Frequency (MHz)')
	ax2.set_ylabel('Magnitude (dB)')
	#ax2.vlines(x=fpeaks/1e6, ymin=min(ly), ymax=max(ly), color="C1")
	ax2.set_xlim([(freq_offset)/1e6, (freq_offset+fs)/1e6+0.5])
	ax2.set_ylim([-40,60])

	ax1.grid()
	ax2.grid()
	
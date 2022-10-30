"""
Embedded Python Blocks:

Each time this file is saved, GRC will instantiate the first class it finds
to get ports and parameters of your block. The arguments to __init__  will
be the parameters. All of them are required to have default values!
"""
import sys
import numpy as np
from gnuradio import gr
from matplotlib import pyplot as plt
from scipy.signal import find_peaks
from configparser import ConfigParser
import json
import pmt
import datetime

# init parser
parser = ConfigParser()
parser.read("/home/ltetest/Desktop/recording-mic-detection/python scripts/airspy/config.ini")
sdr = 'sdrplay'

path_folders = json.loads(parser.get(sdr, 'syspath_addons'))

for folder in path_folders:
    sys.path.append(folder)

import clk_freq_detection as cfd 
import peak_detection as pd
from utils import compute_all_center_frequencies

start_cf = parser.getint(sdr, 'starting_center_freq')
max_harmonic = parser.getint(sdr, 'max_harmonic')
row_size = parser.getint(sdr, 'n_sweeps')
col_size = parser.getint(sdr, 'sampl_per_sweep')
freq_div = parser.getint(sdr, 'freq_per_sweep')
center_freqs = compute_all_center_frequencies(start_cf, freq_div, row_size)

fs = row_size * freq_div
N = row_size * col_size

harmonics = np.arange(1,max_harmonic,2)
n_harmonics = len(harmonics)

# sweep specific
bin_select = parser.get(sdr, 'bin_select')
bin_skip = parser.getint(sdr, 'bin_skip')

# aliasing specific
is_alias = parser.getboolean(sdr, 'is_alias')
if is_alias:
    nyq_freq = parser.getint(sdr, 'nyquist_freq')
else:
    nyq_freq = 0

if bin_select == "both_sided":
    freq_offset = start_cf - freq_div/2
elif bin_select == "right_sided":
    freq_offset = start_cf + int(bin_skip*fs/N)
else:
    print("Error in bin select! Choose right_sided/both_sided")

# peak detection param
height = parser.getfloat(sdr, 'height') #in dB
dist = parser.getfloat(sdr, 'dist') #in samples
# clk freq detection param
score = parser.getint(sdr, 'score')
min_freq = parser.getint(sdr, 'min_freq')
max_freq = parser.getint(sdr, 'max_freq')
err_freq = parser.getfloat(sdr, 'err_freq')

# folder to save data
save_folder = parser.get(sdr, "folder")

# init lists / matrices
logfft_mat = np.zeros([row_size,col_size], dtype=np.float32)

local_ctr = 1
freq_ctr = 0
itr_ctr = 0
itr_score = 0
total_itr = 100


class blk(gr.sync_block):  # other base classes are basic_block, decim_block, interp_block
    """Embedded Python Block example - a simple multiply const"""

    def __init__(self, fft_size=8192, poll_rate=4, fname="tmp.bin"):  # only default arguments here
        self.fft_size = fft_size
        self.poll_rate = poll_rate
        self.fname = fname
        """arguments to this function show up as parameters in GRC"""
        gr.sync_block.__init__(
            self,
            name='1-in-N-peak-detection',   # will show up in GRC
            in_sig=[(np.float32, self.fft_size)],
            # out_sig=[(np.float32, row_size*col_size)]
            out_sig=None
        )
        self.message_port_register_out(pmt.intern('out_port'))


    def work(self, input_items, output_items):
        global freq_bitmap, logfft_mat
        global freq_ctr, local_ctr, itr_ctr, score

        """ changing center freq """
        if local_ctr == self.poll_rate:
            """ save previous center freq data """
            in0 = input_items[0][0]
            if bin_select == "both_sided":
                sidx = int(self.fft_size/2-col_size/2)
                eidx = int(self.fft_size/2+col_size/2)
            elif bin_select == "right_sided":
                sidx = int(self.fft_size/2+bin_skip)
                eidx = int(sidx+col_size)
            else:
                print("Error in bin select! Choose right_sided/both_sided")
            logfft_mat[freq_ctr][:] = in0[sidx:eidx]        


            if freq_ctr == (row_size-1):
                # print("All values satisfied!")
                logfft_list = logfft_mat.flatten()
                ly = logfft_list - np.mean(logfft_list)
                # print(np.shape(ly))
                # xf = (freq_offset + np.linspace(0, fs, N))/1e6
                # plt.plot(xf,ly)
                # plt.show()

                with open(save_folder + self.fname, 'ab') as f:
                    np.save(f, logfft_list, allow_pickle=True)

                logfft_mat = np.zeros([row_size,col_size], dtype=np.float32)

                peaks, _ = pd.amplitude_based(ly, height, dist)
                # print(np.shape(peaks))
                fpeaks = freq_offset + peaks * fs/float(N)
                # print("fpeaks: ", fpeaks/1e6)
                pred_clk_freq_list, _, _ = cfd.detect_clk_freqs(fpeaks, \
                    score, harmonics, min_freq, max_freq, err_freq, nyq_freq)

                now = datetime.datetime.now()
                if pred_clk_freq_list.size != 0:
                    print("Time: ", now.hour,":",now.minute,":",\
                        now.second, ":", round(now.microsecond/1e3), \
                        ", Clock frequency present at ", pred_clk_freq_list, "kHz!!")
                else:
                    print("Time: ", now.hour,":",now.minute,":",\
                        now.second, ":", round(now.microsecond/1e3), \
                        ", Clock frequency NOT present")

            freq_ctr = (freq_ctr+1)%row_size
            new_center_freq = center_freqs[freq_ctr]
            #https://wiki.gnuradio.org/index.php/Soapy#Messages
            # create pmt dict
            msg_dict = pmt.make_dict()
            key0 = pmt.intern("freq") # center freq
            val0 = pmt.from_double(new_center_freq)
            msg_dict = pmt.dict_add(msg_dict, key0, val0)

            self.message_port_pub(pmt.intern("out_port"), msg_dict)
            # print("Switching freq to ", new_center_freq/1e6," MHz")

            local_ctr = 1
        else:
            local_ctr += 1
        return len(input_items[0])
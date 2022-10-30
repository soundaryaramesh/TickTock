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
import RPi.GPIO as gpio
import os
import csv

# init parser
parser = ConfigParser()
parser.read("/home/pi/recording-mic-detection/python scripts/airspy/config.ini")
sdr = 'sdrplay'

path_folders = json.loads(parser.get(sdr, 'rpi_syspath_addons'))

for folder in path_folders:
    sys.path.append(folder)

from utils import compute_all_center_frequencies as comp_cf
from utils import if_acceptable_dist
from detect import detect_per_trial as dpt

start_cf = parser.getint(sdr, 'starting_center_freq')
# max_harmonic = parser.getint(sdr, 'max_harmonic')
row_size = parser.getint(sdr, 'n_sweeps')
col_size = parser.getint(sdr, 'sampl_per_sweep')
freq_div = parser.getint(sdr, 'freq_per_sweep')
center_freqs = comp_cf(start_cf, freq_div, row_size)

# acceptable distance
dist_freq = parser.getfloat(sdr, 'allowable_dist_freq')
# # sweep specific
bin_select = parser.get(sdr, 'bin_select')
# init lists / matrices
logfft_mat = np.zeros([row_size,col_size], dtype=np.float32)

# folder to save data
save_folder = parser.get(sdr, "rpi_folder")

local_ctr = 1
freq_ctr = 0

# setup LEDs
gpin = 4; apin = 23; rpin = 22
gpio.setmode(gpio.BCM)
gpio.setup(gpin, gpio.OUT) #green
gpio.setup(apin, gpio.OUT) #amber
gpio.setup(rpin, gpio.OUT) #red

class blk(gr.sync_block):  # other base classes are basic_block, decim_block, interp_block
    """Embedded Python Block example - a simple multiply const"""

    def __init__(self, fft_size=8192, poll_rate=1, exp_freq='2048', height=20., only_odd_harmonic=False, is_save=False, fname="tmp.bin"):  # only default arguments here
        self.fft_size = fft_size
        self.poll_rate = poll_rate
        self.exp_freq = [int(f) for f in exp_freq.split(',')]
        self.height = height
        self.only_odd_harmonic = only_odd_harmonic
        self.is_save = is_save
        if self.is_save:
            self.fname = fname
            self.fp = open(os.path.join(save_folder, self.fname), 'wb')
            self.tname = self.fname.split('.')[0] + '.csv' # file that logs time
            self.tp = open(os.path.join(save_folder, self.tname), 'w')
            self.writer = csv.DictWriter(self.tp, fieldnames = ["h","m","s","ms","time-diff-ms"])
            self.writer.writeheader()
            
            self.prev_hour = 0
            self.prev_min = 0
            self.prev_sec = 0
            self.prev_ms = 0
        
        parser.set(sdr, 'height', str(self.height))
        if self.only_odd_harmonic:
            print("Odd harmonic: yes")
            parser.set(sdr, 'only_odd_harmonic', 'yes')
        else:
            print("Odd harmonic: no")
            parser.set(sdr, 'only_odd_harmonic', 'no')

        """arguments to this function show up as parameters in GRC"""
        gr.sync_block.__init__(
            self,
            name='1-in-N-peak-detection',   # will show up in GRC
            in_sig=[(np.float32, self.fft_size)],
            # out_sig=[(np.float32, row_size*col_size)]
            out_sig=None
        )
        self.message_port_register_out(pmt.intern('out_port'))
        
    def compute_time_diff(self, now_hour, now_min, now_sec, now_ms):
        td = (now_hour-self.prev_hour)*3600*1e3 + \
             (now_min-self.prev_min)*60*1e3 + \
             (now_sec-self.prev_sec)*1e3 + \
             (now_ms-self.prev_ms)
        return td


    def work(self, input_items, output_items):
        global freq_bitmap, logfft_mat
        global freq_ctr, local_ctr, itr_ctr, score

        """ changing center freq """
        if local_ctr == self.poll_rate:
            """ save previous center freq data """
            in0 = np.fft.fftshift(input_items[0][0])
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
                # print(np.shape(ly))
                # xf = (freq_offset + np.linspace(0, fs, N))/1e6
                # plt.plot(xf,ly)
                # plt.show()
                now = datetime.datetime.now()
                if self.is_save:
                    np.save(self.fp, logfft_list)
                    
                    now_hour = now.hour; now_min = now.minute
                    now_sec = now.second
                    now_ms = round(now.microsecond/1e3)
                    
                    write_dict={}
                    write_dict["h"] = now_hour
                    write_dict["m"]= now_min
                    write_dict["s"] = now_sec
                    write_dict["ms"] = now_ms
                    write_dict["time-diff-ms"] = self.compute_time_diff(now_hour, now_min, now_sec, now_ms)
                    self.writer.writerow(write_dict)
                    
                    self.prev_hour = now_hour
                    self.prev_min = now_min
                    self.prev_sec = now_sec
                    self.prev_ms = now_ms

                logfft_mat = np.zeros([row_size,col_size], dtype=np.float32)
                _, _, _, _, clklist, scorelist, _, _ = dpt(logfft_list, self.height, parser, sdr)
              
                
                n_clk = clklist.size
                if n_clk != 0:
                    print("Time: ", now.hour,":",now.minute,":",\
                        now.second, ":", round(now.microsecond/1e3), \
                       ", Clock frequency present at ", clklist, "kHz!!")
                    if if_acceptable_dist(clklist, self.exp_freq, dist_freq):
                        if n_clk == 1:
                            gpio.output(gpin, gpio.HIGH)
                            gpio.output(apin, gpio.LOW)
                            gpio.output(rpin, gpio.LOW)
                            print("Good location found!!")
                            print("Score: ",scorelist)
                        else:
                            gpio.output(gpin, gpio.LOW)
                            gpio.output(apin, gpio.HIGH)
                            gpio.output(rpin, gpio.LOW)
                    else:
                        gpio.output(gpin, gpio.LOW)
                        gpio.output(apin, gpio.LOW)
                        gpio.output(rpin, gpio.HIGH)
                else:
                    print("Time: ", now.hour,":",now.minute,":",\
                        now.second, ":", round(now.microsecond/1e3), \
                        ", Clock frequency NOT present")
                    gpio.output(gpin, gpio.LOW)
                    gpio.output(apin, gpio.LOW)
                    gpio.output(rpin, gpio.HIGH)

            freq_ctr = (freq_ctr+1)%row_size
            new_center_freq = center_freqs[freq_ctr]
            #https://wiki.gnuradio.org/index.php/Soapy#Messages
            # create pmt dict
            msg_dict = pmt.make_dict()
            key0 = pmt.intern("freq") # center freq
            val0 = pmt.from_double(float(new_center_freq))
            msg_dict = pmt.dict_add(msg_dict, key0, val0)

            self.message_port_pub(pmt.intern("out_port"), msg_dict)
            # print("Switching freq to ", new_center_freq/1e6," MHz")

            local_ctr = 1
        else:
            local_ctr += 1
        return len(input_items[0])

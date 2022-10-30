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
peak_thresh = parser.getfloat(sdr, 'peak_thresh')

center_freqs = [6.6e6,15e6] # always keep the one with peak at the end
print("Center freqs: ", center_freqs)
n_freq = len(center_freqs)

local_ctr = 1
msg_ctr = 0
itr_ctr = 0
score = 0
total_itr = 100

class blk(gr.sync_block):  # other base classes are basic_block, decim_block, interp_block
    """Embedded Python Block example - a simple multiply const"""

    def __init__(self, fft_size=8192, poll_rate=4):  # only default arguments here
        self.fft_size = fft_size
        self.poll_rate = poll_rate
        
        """arguments to this function show up as parameters in GRC"""
        gr.sync_block.__init__(
            self,
            name='Peak per range detection',   # will show up in GRC
            in_sig=[(np.float32, self.fft_size)],
            # out_sig=[(np.float32, row_size*col_size)]
            out_sig=None
        )
        self.message_port_register_out(pmt.intern('out_port'))



    def work(self, input_items, output_items):
        global msg_ctr, local_ctr, itr_ctr, score

        center_freq = center_freqs[msg_ctr]

        """ peak detection """
        ly = input_items[0][0]
        peak_pos = np.argmax(ly)
        peak_val = ly[peak_pos]


        """ changing center freq """
        if local_ctr == self.poll_rate:
            itr_ctr += 1
            if peak_val > peak_thresh:
                if msg_ctr == n_freq - 1: # the last center freq
                    score += 1
                # print("Ctr: ", local_ctr, ", Center freq: ", center_freq/1e6,\
                #    "MHz, Peak found!, Score: ",score,"/",itr_ctr)

            else:
                if msg_ctr != n_freq - 1: # not the last center freq
                    score += 1
                # print("Ctr: ", local_ctr, ", Center freq: ", center_freq/1e6, \
                #    "MHz, No peak!, Score: ",score,"/",itr_ctr)

            if itr_ctr == total_itr:
                now = datetime.datetime.now()
                print("Time: ", now.hour,":",now.minute,":",\
                    now.second,", OVERALL SCORE: ",score,"/",itr_ctr)
                itr_ctr = 0
                score = 0

            msg_ctr = (msg_ctr+1)%n_freq
            new_center_freq = center_freqs[msg_ctr]
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
"""
Embedded Python Blocks:

Each time this file is saved, GRC will instantiate the first class it finds
to get ports and parameters of your block. The arguments to __init__  will
be the parameters. All of them are required to have default values!
"""
# import sys
# sys.path.append("~/gnuradio-folder")

import numpy as np
from gnuradio import gr
# from epy_module_0 import get_f


class blk(gr.sync_block):  # other base classes are basic_block, decim_block, interp_block
    """Embedded Python Block example - a simple multiply const"""

    def __init__(self, fft_size=8192, center_freq=2e6):  # only default arguments here
        # if an attribute with the same name as a parameter is found,
        # a callback is registered (properties work, too).
        self.fft_size = fft_size
        self.center_freq = center_freq

        """arguments to this function show up as parameters in GRC"""
        gr.sync_block.__init__(
            self,
            name='FFT Shift',   # will show up in GRC
            in_sig=[(np.float32, self.fft_size)],
            out_sig=[(np.float32, self.fft_size)]
        )
        

    def work(self, input_items, output_items):
        # print("Center freq: ", self.center_freq)
        # print(epy_module_0.get_f())
        """example: multiply with constant"""
        in0 = input_items[0]
        out0_1 = np.fft.fftshift(in0)
        # shift the dB level such that the mean is 0
        # print(np.max(in0))
        avg_db_level = 0#np.average(in0)
        out0_2 = out0_1 - avg_db_level
        output_items[0][0]   = out0_2
        return len(output_items[0])

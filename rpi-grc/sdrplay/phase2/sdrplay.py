#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#
# SPDX-License-Identifier: GPL-3.0
#
# GNU Radio Python Flow Graph
# Title: RSP1A
# Author: ltetest
# GNU Radio version: 3.8.2.0

from gnuradio import gr
from gnuradio.filter import firdes
import sys
import signal
from argparse import ArgumentParser
from gnuradio.eng_arg import eng_float, intx
from gnuradio import eng_notation
from gnuradio.fft import logpwrfft
import epy_block_0
import soapy
import distutils
from distutils import util


class sdrplay(gr.top_block):

    def __init__(self):
        gr.top_block.__init__(self, "RSP1A")

        ##################################################
        # Variables
        ##################################################
        self.filter_bandwidth = filter_bandwidth = 8e6
        self.fft_size = fft_size = 8192
        self.center_freq = center_freq = 4.6e6
        self.bandwidth = bandwidth = 10e6

        ##################################################
        # Blocks
        ##################################################
        self.soapy_source_0 = None
        # Make sure that the gain mode is valid
        if('Overall' not in ['Overall', 'Specific', 'Settings Field']):
            raise ValueError("Wrong gain mode on channel 0. Allowed gain modes: "
                  "['Overall', 'Specific', 'Settings Field']")

        dev = 'driver=sdrplay'

        # Stream arguments for every activated stream
        tune_args = ['']
        settings = ['']

        # Setup the device arguments

        dev_args = "if_mode=Zero-IF, agc_setpoint=-30, biasT_ctrl=false, rfnotch_ctrl=false, dabnotch_ctrl=false"

        self.soapy_source_0 = soapy.source(1, dev, dev_args, '',
                                  tune_args, settings, bandwidth, "fc32")



        self.soapy_source_0.set_dc_removal(0,bool(distutils.util.strtobool('True')))

        # Set up DC offset. If set to (0, 0) internally the source block
        # will handle the case if no DC offset correction is supported
        self.soapy_source_0.set_dc_offset(0,0)

        # Setup IQ Balance. If set to (0, 0) internally the source block
        # will handle the case if no IQ balance correction is supported
        self.soapy_source_0.set_iq_balance(0,0)

        self.soapy_source_0.set_agc(0,False)

        # generic frequency setting should be specified first
        self.soapy_source_0.set_frequency(0, center_freq)

        self.soapy_source_0.set_frequency(0,"BB",0)

        # Setup Frequency correction. If set to 0 internally the source block
        # will handle the case if no frequency correction is supported
        self.soapy_source_0.set_frequency_correction(0,0)

        self.soapy_source_0.set_antenna(0,'RX')

        self.soapy_source_0.set_bandwidth(0,filter_bandwidth)

        if('Overall' != 'Settings Field'):
            # pass is needed, in case the template does not evaluare anything
            pass
            self.soapy_source_0.set_gain(0,10)
        self.logpwrfft_x_0 = logpwrfft.logpwrfft_c(
            sample_rate=bandwidth,
            fft_size=fft_size,
            ref_scale=2,
            frame_rate=5,
            avg_alpha=0.1,
            average=False)
        self.epy_block_0 = epy_block_0.blk(fft_size=fft_size, poll_rate=1, exp_freq='2048', height=20, only_odd_harmonic=1, is_save=0, fname="l21x_det_2_no_mic_h20.bin")



        ##################################################
        # Connections
        ##################################################
        self.msg_connect((self.epy_block_0, 'out_port'), (self.soapy_source_0, 'command'))
        self.connect((self.logpwrfft_x_0, 0), (self.epy_block_0, 0))
        self.connect((self.soapy_source_0, 0), (self.logpwrfft_x_0, 0))


    def get_filter_bandwidth(self):
        return self.filter_bandwidth

    def set_filter_bandwidth(self, filter_bandwidth):
        self.filter_bandwidth = filter_bandwidth
        self.soapy_source_0.set_bandwidth(0,self.filter_bandwidth)

    def get_fft_size(self):
        return self.fft_size

    def set_fft_size(self, fft_size):
        self.fft_size = fft_size
        self.epy_block_0.fft_size = self.fft_size

    def get_center_freq(self):
        return self.center_freq

    def set_center_freq(self, center_freq):
        self.center_freq = center_freq
        self.soapy_source_0.set_frequency(0, self.center_freq)

    def get_bandwidth(self):
        return self.bandwidth

    def set_bandwidth(self, bandwidth):
        self.bandwidth = bandwidth
        self.logpwrfft_x_0.set_sample_rate(self.bandwidth)





def main(top_block_cls=sdrplay, options=None):
    tb = top_block_cls()

    def sig_handler(sig=None, frame=None):
        tb.stop()
        tb.wait()

        sys.exit(0)

    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    tb.start()

    try:
        input('Press Enter to quit: ')
    except EOFError:
        pass
    tb.stop()
    tb.wait()


if __name__ == '__main__':
    main()

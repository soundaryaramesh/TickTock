# all the imports go here
import sys
import os
import csv
import numpy as np
from configparser import ConfigParser
from mic_freq_identification import mic_freq_id
from datetime import datetime
sys.path.append("../")
from utils import save_config_logs

if __name__ == '__main__':
	# read binary log fft data from file
	if len(sys.argv) != 3:
		print("Format python3 ", sys.argv[0], " <calibration-info-file-name> <device_type>")
		sys.exit(1)

	# init param
	cal_fname = sys.argv[1]
	device_type = sys.argv[2]
	all_sdrs = ["rtlsdr", "airspy", "uhd"]
	max_traces = {}; oe_hmonic = {}
	max_traces['rtlsdr'] = 330; max_traces['airspy'] = 75; max_traces['uhd'] = 1720	
	oe_hmonic['rtlsdr'] = 'yes'; oe_hmonic['airspy'] = 'yes'; oe_hmonic['uhd'] = 'yes'

	# init parser
	parser = ConfigParser()
	parser.read("/home/ltetest/Desktop/recording-mic-detection/python scripts/airspy/config.ini")
	
	# init detection file
	now = datetime.now()
	str_time = now.strftime("%S-%M-%H-%d-%m-%Y")
	dirname = os.path.dirname(cal_fname)
	det_fname =  os.path.join(dirname, \
		device_type + "-diff-SDR-calibration-output-" + str_time + ".csv")
	print("Detection file name: ", det_fname)
	# config log file
	config_fname = os.path.join(dirname, "config-logs", \
		device_type + "-diff-SDR-calibration-output-" + str_time)
	
	# init column names
	det_fields = ["folder", "probe", "detect-mic-file", "detect-no-mic-file", \
	"sdr", "freq", "height", "only_odd_harmonic"]
	detf = open(det_fname, mode='w')
	det_writer = csv.DictWriter(detf, fieldnames=det_fields)
	det_writer.writeheader()

	with open(cal_fname, mode='r') as f:
		csv_reader = csv.DictReader(f)
		device_info_rows = list(csv_reader)
	for row in device_info_rows:
		det_dict = {}
		folder_name = row["folder"]
		mic_file = row["mic-file"]
		nomic_file = row["no-mic-file"]
		sdr = row["sdr"]
		probe = row["probe"]
		# set calibration flag to yes
		parser.set(sdr, 'config_mode', 'yes')
		parser.set('calibrate', 'diff_sdr', 'yes')	
		parser.set(sdr, 'folder', folder_name)
		# set O/E harmonic - based on sdrplay 
		print("Setting only-odd-harmonic to ", oe_hmonic[sdr])
		parser.set(sdr,'only_odd_harmonic', oe_hmonic[sdr])

		# setting min-count
		sdr_cutoff = parser.getfloat('calibrate', 'sdr_cutoff')
		min_count = round(sdr_cutoff * max_traces[sdr])
		parser.set('calibrate', 'min_count', str(min_count))
		print("Setting min-count to: ", parser.getint('calibrate', 'min_count'))

		print("Device: ", os.path.basename(folder_name)) # print final dir
		print("Probe: ", probe)
		mic_clk, _, mic_oe_bool, mic_ampl = mic_freq_id(mic_file, nomic_file, parser, sdr)

		if mic_clk.size == 0:
			print("-"*150)
			print("-"*150)
			continue
		det_mic_file = mic_file.replace("cal", "det")
		# if detection file doesn't exist
		if not(os.path.exists(os.path.join(folder_name,det_mic_file+'.bin'))):
			print("File: ", det_mic_file, " does not exist!")
			print("-"*150)
			print("-"*150)
			continue

		det_dict["folder"] = folder_name
		det_dict["probe"] = probe
		det_dict["sdr"] = sdr
		det_dict["detect-mic-file"] = det_mic_file
		det_dict["detect-no-mic-file"] = det_mic_file.replace("_mic_","_no_mic_")
		det_dict["freq"] = str(mic_clk)
		det_dict["height"] = str(np.array(np.floor(mic_ampl), dtype=int))
		if mic_oe_bool:
			det_dict["only_odd_harmonic"] = 'yes'
		else:
			det_dict["only_odd_harmonic"] = 'no'
		det_writer.writerow(det_dict)

		print("-"*150)
		print("-"*150)

	for sdr in all_sdrs:
		sdr_config_fname = config_fname+"-"+sdr+".json"
		save_config_logs(sdr_config_fname, parser, sdr) # assumes only single SDR!


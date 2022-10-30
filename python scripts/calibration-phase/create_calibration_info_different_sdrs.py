import sys
import csv
import os
import re
from datetime import datetime

def atoi(text):
    return int(text) if text.isdigit() else text

def natural_keys(text):
    '''
    alist.sort(key=natural_keys) sorts in human order
    http://nedbatchelder.com/blog/200712/human_sorting.html
    (See Toothy's implementation in the comments)
    '''
    return [ atoi(c) for c in re.split(r'(\d+)', text) ]


if __name__ == '__main__':
	# read binary log fft data from file
	if len(sys.argv) != 4:
		print("Format python3", sys.argv[0], "<devices-path> <device-type> <csv_path>")
		sys.exit(1)

	devices_path = sys.argv[1]
	device_type = sys.argv[2]
	csv_path = sys.argv[3]

	banned_sdrs = ["sdrplay"]

	# init calibration file
	now = datetime.now()
	str_time = now.strftime("%S-%M-%H-%d-%m-%Y")	
	calib_fname = os.path.join(csv_path, \
		device_type + "-diff-SDR-calibration-info-" + str_time + ".csv")

	# setup the column headers
	fields = ["folder", "probe", "mic-file", "no-mic-file", "sdr"]
	fw = open(calib_fname, mode = "w")
	writer = csv.DictWriter(fw, fieldnames=fields)
	writer.writeheader()

	# find all device folders from device path
	subdirs = os.listdir(devices_path)
	# sort the subdirs
	# https://stackoverflow.com/questions/5967500/how-to-correctly-sort-a-string-with-a-number-inside
	subdirs.sort(key = natural_keys)

	for subdir in subdirs:
		sdr = subdir 
		if sdr in banned_sdrs:
			continue
		sdr_path = os.path.join(devices_path, subdir)
		laptop_subdirs = os.listdir(sdr_path)
		for laptop_subdir in laptop_subdirs:
			full_device_path = os.path.join(sdr_path, laptop_subdir)
			if os.path.isfile(full_device_path) or laptop_subdir == "tmp":
				continue # probably some tmp files
			files = os.listdir(full_device_path)
			# shortlist only calibration - mic files
			cal_mic_files = [f for f in files if '_cal_' in f and \
				'mic' in f.split('_')[3] and 'tmp' not in f]
			cal_mic_files.sort()
			for cal_mic_file in cal_mic_files:
				cal_no_mic_file = cal_mic_file.replace("_mic_","_no_mic_")
				probe = ['h-field' if 'h' in cal_mic_file.split('_')[-1] \
					else 'e-field' if 'e' in cal_mic_file.split('_')[-1] else '']
				probe = probe[0]

				cal_dict = {}
				cal_dict['folder'] = full_device_path
				cal_dict['probe'] = probe
				cal_dict['mic-file'] = cal_mic_file.split('.')[0] # remove ext
				cal_dict['no-mic-file'] = cal_no_mic_file.split('.')[0]
				cal_dict['sdr'] = sdr
				writer.writerow(cal_dict)

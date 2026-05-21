import os
import statistics
import ccc_fns as cf

"""
allan_dev.py

This script takes CCC bvd.txt data files and outputs a .dat file, suitable as input to
Stable32 which is used to generate Allan deviation plots of the data.
"""

TIMEBASE = 0.02  # One 50 Hz cycle.

folder = input('Path to CCC BVD file: ')  # E.g. ...\Magnicon CCC\Commissioning\Data\2024-08-15_CCC
filename = input('BVD file name: ')  # E.g. 240815_002_1628_bvd.txt
basename = filename.split('.')[0]
print(f'basename: "{basename}"')
dir_filename = os.path.join(folder, filename)
print(dir_filename)

"""
Open bvd file and read values into a list (ignoring header).
"""
bvd_vals = []
with open(dir_filename, 'r') as bvd_file:
    line = bvd_file.readline()  # 1st line
    while line[0] != '#':  # Header line before 1st data row (on exit)
        line = bvd_file.readline()
        if line.startswith('integration time'):
            sampletime = TIMEBASE*float(line.split(':')[1].strip())  # in s
        if line.startswith('number of samples per half cycle'):
            samples_per_cycle = 2*float(line.split(':')[1].strip())
            cycletime = samples_per_cycle*sampletime

    while True:
        line = bvd_file.readline()  # data row
        if not line:
            break  # break at EOF
        bvd = float(line.split()[1])  # Split at " ", cast 2nd item as float
        bvd_vals.append(bvd)
print(f'End of file - read {len(bvd_vals)} values.\n')

"""
Truncation cut: remove 'dead' points from end of file, in case of SQUID-lock-loss
"""
bvd_vals_trunc = cf.truncate(bvd_vals)
av_value_trunc, sd_trunc = cf.mean_and_sd(bvd_vals)  # statistics.mean(bvd_vals_trunc)
print(f'Cut {len(bvd_vals) - len(bvd_vals_trunc)} points. Mean bvd (truncated) = {av_value_trunc:.2e} V')

"""
Data quality cut: remove outliers.
"""
bvd_vals_kept, bvd_vals_kept_av, threshold, n_sig = cf.cut_outliers(bvd_vals_trunc)
print(f'Retained {len(bvd_vals_kept)} values with mean value {bvd_vals_kept_av:.2e} V')
if threshold == 0:
    print(f'Excluded no points.')
else:
    print(f'Excluded points more than {threshold:.2e} V ({n_sig:.2f} sigma) from the mean')

"""
Write out a 'cleaned' version of the data
"""
outfilename = f'{basename}.dat'
dir_filename = os.path.join(folder, outfilename)
with open(dir_filename, 'w') as dat_file:
    cycle_count = 0
    for val in bvd_vals_kept:
        cycle_count += 1
        line = f'{cycle_count*cycletime/86400:.6f}\t{val}\n'  # N*cycles, expressed in days.
        dat_file.write(line)

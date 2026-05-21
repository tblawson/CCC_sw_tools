"""
clean.py

A script to reduce noise in bvd data.

The raw bvd values are split into N equal-sized bins of n points and a new array
of N standard deviations generated. All bins with a standard deviation greater than
k*[the minimum standard deviation] are flagged. Bins in the original data are cut if the
corresponding bin in the standard deviation array is flagged. The resulting 'cleaned'
bvd file is written to the same filename under a new folder called '\cleaned\'.
"""

import ccc_fns as cf
import math

MINBINWIDTH = 5
N_SIGMA = 2  # Default to 2-sigma cut

runs_dict, data_dir = cf.present_runs()  # List data dirs and prompt for selection

# File-wrangling:
run_num_str_choice = input('Enter run number (xxx), or e to exit: ')
bvd_file = runs_dict[run_num_str_choice]['bvd_file']
basename = cf.parse_filename(bvd_file)['basename']
print(f'\nSelected bvd file: \t\t{bvd_file}')  # e.g: 260512_009_1539_bvd.txt
in_filepath = cf.make_full_path(data_dir, bvd_file)
out_filepath = cf.make_full_path(f'{data_dir}\\cleaned', bvd_file)

# Read raw bvd data:
raw_bvd_vals = cf.get_bvd_data(in_filepath)

'''
Divide raw data array into the largest number of bins that ensure:
* All bins are the >= minimum size (MINBINWIDTH)
* All raw data points are included.
This can be implemented by ensuring the last bin includes any 'overflow'.
Next:
1. Determine the sd for each bin. Note the minimum sd.
2. Eliminate each bin from the raw data where its sd is larger than k * minimum sd.
'''

index = 0
all_bins = []
all_sds = []
prev_bin = []
min_sd = 1  # 1 V is huge, so this is an effective max value.
min_sd_index = 0
while True:  # This loop determines which bin has the minimum sd.
    end_index = index + MINBINWIDTH
    if end_index > len(raw_bvd_vals):
        all_bins.pop()  # Discard previous bin and replace it with...
        all_sds.pop()
        this_bin = prev_bin + raw_bvd_vals[index:]  # ...previous bin and leftovers
        break_flag = True
    else:
        this_bin = raw_bvd_vals[index:end_index]
    prev_bin = this_bin
    all_bins.append(this_bin)
    this_mean, this_sd = cf.mean_and_sd(this_bin)
    all_sds.append(this_sd)
    if this_sd <= min_sd:  # Update minimum sd and its start-index.
        min_sd = this_sd
        min_sd_index = index
    if break_flag:
        break
    index += MINBINWIDTH

for  in

# ----------------------------------------------------------------------
clean_bvd_vals = []
bin_list = []
bin_sd_list = []
prev_bin = []

min_sd = 1  # 1 V is huge, so this is an effective max value.
for index in range(0, len(raw_bvd_vals), MINBINWIDTH):
    start_index = index
    end_index = int(start_index + MINBINWIDTH) - 1
    if end_index > len(raw_bvd_vals) - 1:  # Keep index within range (creates a 'runt' bin)
        end_index = len(raw_bvd_vals) - 1
    this_bin = raw_bvd_vals[start_index:end_index+1]  # Define the contents of this bin
    if len(this_bin) < MINBINWIDTH:
        this_bin = prev_bin + this_bin  # Add 'runt' to previous full bin
        bin_list.pop()  # Delete previous bin form bin_list
        bin_sd_list.pop()  # Delete previous bin sd form bin_sd_list
    bin_list.append(this_bin)  # Replace previous full bin with [bin + runt]
    prev_bin = this_bin  # Remember previous bin
    this_mean, this_sd = cf.mean_and_sd(this_bin)
    bin_sd_list.append(this_sd)


bin_count = 0
for sd in bin_sd_list:
    if sd > 2*min_sd:
        bin_list.pop(bin_count)  # Discard this bin for being too noisy.
    bin_count += 1
# ----------------------------------------------------------------------
print(bin_list)

# Test cut_outliers():
# bvd_vals_kept, bvd_vals_kept_av, threshold, n_sig = cf.cut_outliers(raw_bvd_vals)
# print(f'Retained {len(bvd_vals_kept)} values with mean value {bvd_vals_kept_av:.2e} V')
# print(f'Excluded points more than {threshold:.2e} V ({n_sig:.2f} sigma) from the mean.')

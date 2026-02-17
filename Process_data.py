"""
Process_data.py

A script to open and read Magnicon CCC bvd files and extract data,
calculate the resistor ratio and write to the CCC.db database.
    Tim Lawson
    12/12/2025
"""
import os
import GTC
import math

ROOTDATADIR = r'C:\Users\t.lawson\Callaghan Innovation\ORG-MSL [MSL] - Electricity' \
              r'\Ongoing\QHR_CCC\Magnicon CCC\Commissioning\Data'
k_unc_decode = {'0': 512, '1': 64, '2': 8, '3': 1}


# --------------------USEFUL FUNCTIONS--------------------
def extract_parameter(filepath, param, sep):
    """
    Search file filepath for param (where sep is the delimiter between param and the value)
    and return corresponding value (as a string).
    """
    with open(filepath, 'r') as file_p:
        for line in file_p.readlines():
            if param in line:
                return line.split(sep)[1].strip()  # Everything to right of sep, without surrounding whitespace.
            else:
                continue  # Skip to next line.
        return ''  # Return empty string if param not found.


def extract_bvd(filepath):
    """
    Return 3rd and 4th fields from the last line of the file (as floats).
    """
    with open(filepath, 'r') as file_p:
        lines = file_p.readlines()
        # Check bvd averages is greater than zero:
        assert int(lines[8].split(':')[1].strip()) > 0, 'No bvd data available!'

        bvd_av = lines[-1].split()[2]  # last row, 3rd field
        bvd_sd = lines[-1].split()[3]  # last row, 4th field
        return float(bvd_av), float(bvd_sd)


def parse_filename(file):
    """
    Return <date_str>, <run_num_str>, <time_str>, <filetype>
    :param file: (str) filename to parse. E.g.: 260203_001_1127.txt, 260203_001_1127_bvd, 260203_001_1127_cccdrive.cfg
    :return: dict containing above keys.
    """
    file_data = {'date_str': '', 'run_num_str': '', 'time_str': '', 'type': ''}
    file_parts = file.split('_')
    if file.endswith('.txt') or file.endswith('.cfg'):
        file_data['date_str'] = file_parts[0]
        file_data['run_num_str'] = file_parts[1]
        file_data['time_str'] = file_parts[2]
        if len(file_parts) < 4:
            file_data['type'] = ''
        else:
            file_data['type'] = file_parts[3]
    return file_data


def create_runtable(filelist):
    """
    Collate info on data files. Group by run number
    :param filelist: list of data files
    :return: dict, keyed by run_num_str.
    """
    runtable = {}
    for file in filelist:
        f_data_dict = parse_filename(file)
        run_str = f_data_dict['run_num_str']
        file_type = f_data_dict['type']
        if run_str == '':
            continue  # Skip - not a valid run file.
        else:
            runtable.setdefault(run_str, {})  # Add run item if it doesn't exist. Do nothing otherwise.
        if file_type == 'bvd.txt':
            runtable[run_str]['bvd_file'] = file
        elif file_type == 'cccdrive.cfg':
            runtable[run_str]['cfg_file'] = file
        else:
            continue  # Ignore other data file types.
    return runtable


# ----------------------MAIN SCRIPT---------------------
contents = os.listdir(ROOTDATADIR)
print('\nAvailable data directories:')
for item in contents:
    if '.' in item:
        continue
    print(item)
data_dir = input('Enter directory: ')  # One day's-worth of files.

data_path = os.path.join(ROOTDATADIR, data_dir)  # One day's-worth of files.
data_dir_contents = os.listdir(data_path)
runs_dict = create_runtable(data_dir_contents)

print('\nAvailable runs:')
good_run_count = 0
for run in runs_dict.keys():
    cfgfilepath = os.path.join(ROOTDATADIR, data_dir, runs_dict[run]['cfg_file'])
    bvdfilepath = os.path.join(ROOTDATADIR, data_dir, runs_dict[run]['bvd_file'])
    cal_mode = extract_parameter(cfgfilepath, 'cn_calmode 3', '=')
    non_cn_mode = extract_parameter(cfgfilepath, 'cn_short 3', '=')
    n_bvd = int(extract_parameter(bvdfilepath, 'bvd averages', ':'))
    if cal_mode == 'FALSE' or non_cn_mode == 'TRUE' or n_bvd == 0:
        continue  # Skip this file if not a CN run or calibration mode is OFF or no bvd values.
    else:
        run_num_str = run
        criteria_met_msg = f'calmode = {cal_mode}, CN mode is ON, n_bvd is non-zero ({n_bvd}).'
        good_run_count += 1
    print(f'Run number {run_num_str}:\t\t{criteria_met_msg}')

assert good_run_count > 0, 'No suitable runs available!'

run_num_str_choice = input('Enter run number (xxx): ')
bvd_file = runs_dict[run_num_str_choice]['bvd_file']
config_file = runs_dict[run_num_str_choice]['cfg_file']
print(f'\nSelected bvd file: \t\t{bvd_file}')
print(f'Selected config file: \t{config_file}')

datafilepath = os.path.join(ROOTDATADIR, data_dir, bvd_file)
conffilepath = os.path.join(ROOTDATADIR, data_dir, config_file)

# Extract useful data:
bvd_val, bvd_unc = extract_bvd(datafilepath)

# date_str = extract_parameter(datafilepath, 'stop date', ':')
# time_str = extract_parameter(datafilepath, 'stop time', ':')
n = int(extract_parameter(datafilepath, 'bvd averages', ':'))
R1_name = extract_parameter(datafilepath, 'R1 Info', ':')
R2_name = extract_parameter(datafilepath, 'R2 Info', ':')
k_val_mturns = float(extract_parameter(datafilepath, 'delta N1/NA (mTurns)', ':'))  # in milliturns!
I2R2 = float(extract_parameter(datafilepath, 'delta (I2*R2) (V)', ':'))
N1 = int(extract_parameter(datafilepath, 'N1 (Turns)', ':'))
N2 = int(extract_parameter(datafilepath, 'N2 (Turns)', ':'))
Na = int(extract_parameter(datafilepath, 'NA (Turns)', ':'))
R1_nom = float(extract_parameter(datafilepath, 'R1 (Ohm)', ':'))
R2_nom = float(extract_parameter(datafilepath, 'R2 (Ohm)', ':'))
bvd_df = n-1

if k_val_mturns == 0.0:  # Deal with zero-valued k
    k_val_mturns = float(input('Missing k value! Enter mturns value manually: '))

range_shunt_code = extract_parameter(conffilepath, 'cn_rangeshunt 3', '=')

# Uncert is based on digitisation limit (see GUM2008, sections F.2.2.1 or F.2.2.3):
k_unc = (1/math.sqrt(12)) / 2048 / k_unc_decode[range_shunt_code]

# Build ureals & calculate ratio
bvd = GTC.ureal(bvd_val, bvd_unc, bvd_df, label='bvd')
print(f'bvd(CN run) = {bvd:.2g}')
k = GTC.ureal(k_val_mturns/1000, k_unc, 8, label='k_turns')
print(f'k ={k}')

ratio1_2 = (N1/N2)*(1 + k*Na/N1)*(1 + bvd/I2R2)  # Uncert on I2R2??
print(f'\nCalculated ratio {R1_name}/{R2_name} = {ratio1_2.x:.12f} +/- {ratio1_2.u:.2g}, dof {ratio1_2.df:2.1f}')

ratio_dev_from_nom = ratio1_2 - R1_nom/R2_nom
print(f'Ratio deviation from nominal: {ratio_dev_from_nom:.2e}')

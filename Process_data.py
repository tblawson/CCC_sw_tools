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
def get_filename(dir_path, run_num, fileflag):
    """
    Select bvd filename or config filename, based on run number and file type.
    :param dir_path: (str) directory to search.
    :param run_num: (str) run number (3 digits).
    :param fileflag: (str) switch for file type: 'bvd.txt' or 'cccdrive.cfg'.
    :return: (str) filename (empty string if unsuccessful).
    """
    filelist = os.listdir(dir_path)
    for filename in filelist:
        if run_num in filename and filename.endswith(fileflag):
            return filename
        else:
            continue
    print("Can't find file!")
    return ''


def extract_parameter(filepath, param, sep):
    """
    Search file filepath for param (where sep is the delimiter between param and the value)
    and return corresponding value (as a string).

    Default behaviour is different! -
    Return 3rd and 4th fields from the last line of the file (as floats).
    """
    with open(filepath, 'r') as file_p:
        if param == '':  # Default is to extract bvd value & uncert (as floats).
            lines = file_p.readlines()
            assert int(lines[8].split(':')[1].strip()) > 0, 'No bvd data available!'
            bvd_av = lines[-1].split()[2]  # last row, 3rd field
            bvd_sd = lines[-1].split()[3]  # last row, 4th field
            return float(bvd_av), float(bvd_sd)
        else:  # Extract arbitrary parameter
            for line in file_p.readlines():
                if param in line:
                    return line.split(sep)[1].strip()  # Everything to right of sep, without surrounding whitespace.
                else:
                    continue


# ----------------------MAIN SCRIPT---------------------
contents = os.listdir(ROOTDATADIR)
print('\nAvailable data directories:')
for item in contents:
    if '.' in item:
        continue
    print(item)
data_dir = input('Enter directory: ')

data_path = os.path.join(ROOTDATADIR, data_dir)
data_dir_contents = os.listdir(data_path)

print('\nAvailable data files (calibration mode is ON, CN network is ON):')
for item in data_dir_contents:
    testfilepath = os.path.join(ROOTDATADIR, data_dir, item)
    # if item.endswith('bvd.txt'):
    #     n = int(extract_parameter(testfilepath, 'bvd averages', ':'))
    #     if n < 12:
    #         continue  # skip this file
    #     else:
    #         crit = f'n ={n}'
    if item.endswith('cccdrive.cfg'):
        cal_mode = extract_parameter(testfilepath, 'cn_calmode 3', '=')
        non_cn_mode = extract_parameter(testfilepath, 'cn_short 3', '=')
        if cal_mode == 'FALSE' or non_cn_mode == 'TRUE':
            continue  # skip this file
        else:
            run_num_str = item.split('_')[1]
            crit = f'calmode = {cal_mode}, CN mode is ON'
    else:
        continue  # skip this file
    print(f'Run number {run_num_str}:\t\t({crit}).')
run_num_str = input('Enter run number (xxx): ')
bvd_file = get_filename(data_path, run_num_str, 'bvd.txt')
print(f'\nSelected bvd file: \t\t{bvd_file}')
config_file = get_filename(data_path, run_num_str, 'cccdrive.cfg')
print(f'Selected config file: \t{config_file}')

datafilepath = os.path.join(ROOTDATADIR, data_dir, bvd_file)
conffilepath = os.path.join(ROOTDATADIR, data_dir, config_file)

# Extract useful data:
bvd_val, bvd_unc = extract_parameter(datafilepath, '', '')
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
range_shunt_code = extract_parameter(conffilepath, 'cn_rangeshunt 3', '=')

# Uncert is based on digitisation limit (see GUM2008, sections F.2.2.1 or F.2.2.3):
k_unc = (1/math.sqrt(12)) / 2048 / k_unc_decode[range_shunt_code]

# Build ureals & calculate ratio
bvd = GTC.ureal(bvd_val, bvd_unc, bvd_df, label='bvd')
print(f'bvd(CN run) = {bvd:.2g}')
k = GTC.ureal(k_val_mturns/1000, k_unc, 8, label='k_turns')
print(f'k = {k}')

ratio1_2 = (N1/N2)*(1 + k*Na/N1)*(1 + bvd/I2R2)  # Uncert on I2R2??
print(f'\nCalculated ratio {R1_name}/{R2_name} = {ratio1_2.x} +/- {ratio1_2.u:.2g}, dof {ratio1_2.df:2.1f}')

ratio_dev_from_nom = ratio1_2 - R1_nom/R2_nom
print(f'Ratio deviation: {ratio_dev_from_nom:.2e}')

"""
Process_CCC_data.py

A script to open and read Magnicon CCC bvd files and extract data,
calculate the resistor ratio and write to the CCC.db database.
    Tim Lawson
    12/12/2025
"""
import os
import GTC
import math
import ccc_fns as cf

# ROOTDATADIR = r'C:\Users\t.lawson\Callaghan Innovation\ORG-MSL [MSL] - Electricity' \
#               r'\Ongoing\QHR_CCC\Magnicon CCC\Commissioning\Data'
ROOTDATADIR = r'C:\Users\t.lawson\Callaghan Innovation\ORG-MSL [MSL] - Electricity' \
              r'\Ongoing\QHR_CCC\Magnicon CCC\Measurements\Data'

k_unc_decode = {'0': 512, '1': 64, '2': 8, '3': 1}


# ----------------------MAIN SCRIPT---------------------
# Connect to CCC database:
db_connection = cf.db_connect()
curs = db_connection.cursor()
db_write = False  # Default behaviour is to NOT write to the database.

contents = os.listdir(ROOTDATADIR)
print('\nAvailable data directories:')
for item in contents:
    if '.' in item:
        continue
    print(item)
data_dir = input('Enter directory: ')  # One day's-worth of files.

data_path = os.path.join(ROOTDATADIR, data_dir)  # One day's-worth of files.
data_dir_contents = os.listdir(data_path)
runs_dict = cf.create_runtable(data_dir_contents)

print('\nAvailable runs:')
good_run_count = 0
for run in runs_dict.keys():
    cfgfilepath = os.path.join(ROOTDATADIR, data_dir, runs_dict[run]['cfg_file'])
    bvdfilepath = os.path.join(ROOTDATADIR, data_dir, runs_dict[run]['bvd_file'])
    if cf.extract_parameter(bvdfilepath, 'bvd averages', ':').startswith('x'):
        print(f'Skipping unfinished run {run}.')
        continue  # Skip - Unfinished run
    cal_mode = cf.extract_parameter(cfgfilepath, 'cn_calmode 3', '=')
    non_cn_mode = cf.extract_parameter(cfgfilepath, 'cn_short 3', '=')
    n_bvd = int(cf.extract_parameter(bvdfilepath, 'bvd averages', ':'))
    if cal_mode == 'FALSE' or non_cn_mode == 'TRUE' or n_bvd <= 1:
        continue  # Skip this file if not a CN run or calibration mode is OFF or no bvd values.
    else:
        run_num_str = run
        criteria_met_msg = f'calmode = {cal_mode}, CN mode is ON, n_bvd > 1 ({n_bvd}).'
        good_run_count += 1
    print(f'Run number {run_num_str}:\t\t{criteria_met_msg}')
assert good_run_count > 0, 'No suitable runs available!'

# ----------------run loop-----------------------
while True:
    run_num_str_choice = input('Enter run number (xxx), or e to exit: ')
    if run_num_str_choice == 'e':
        break

    bvd_file = runs_dict[run_num_str_choice]['bvd_file']
    basename = cf.parse_filename(bvd_file)['basename']
    config_file = runs_dict[run_num_str_choice]['cfg_file']
    print(f'\nSelected bvd file: \t\t{bvd_file}')
    print(f'Selected config file: \t{config_file}')

    datafilepath = os.path.join(ROOTDATADIR, data_dir, bvd_file)
    conffilepath = os.path.join(ROOTDATADIR, data_dir, config_file)

    # Extract useful data:
    bvd_val, bvd_unc = cf.extract_bvd(datafilepath)

    # date_str = extract_parameter(datafilepath, 'stop date', ':')
    # time_str = extract_parameter(datafilepath, 'stop time', ':')
    n = int(cf.extract_parameter(datafilepath, 'bvd averages', ':'))
    R1_name = cf.extract_parameter(datafilepath, 'R1 Info', ':')
    R2_name = cf.extract_parameter(datafilepath, 'R2 Info', ':')
    gain = int(cf.extract_parameter(datafilepath, 'amplifier gain', ':'))
    k_val_mturns = float(cf.extract_parameter(datafilepath, 'delta N1/NA (mTurns)', ':'))  # in milliturns!
    I2R2 = float(cf.extract_parameter(datafilepath, 'delta (I2*R2) (V)', ':'))
    N1 = int(cf.extract_parameter(datafilepath, 'N1 (Turns)', ':'))
    N2 = int(cf.extract_parameter(datafilepath, 'N2 (Turns)', ':'))
    Na = int(cf.extract_parameter(datafilepath, 'NA (Turns)', ':'))
    R1_nom = float(cf.extract_parameter(datafilepath, 'R1 (Ohm)', ':'))
    R2_nom = float(cf.extract_parameter(datafilepath, 'R2 (Ohm)', ':'))
    bvd_df = n-1

    if k_val_mturns == 0.0:  # Deal with zero-valued k
        k_val_mturns = float(input('Missing k value! Enter mturns value manually: '))

    range_shunt_code = cf.extract_parameter(conffilepath, 'cn_rangeshunt 3', '=')

    # Uncert is based on digitisation limit (see GUM2008, sections F.2.2.1 or F.2.2.3):
    k_unc = (1/math.sqrt(12)) / 2048 / k_unc_decode[range_shunt_code]

    # Build ureals & calculate ratio
    bvd = GTC.ureal(bvd_val, bvd_unc, bvd_df, label='bvd')
    print(f'bvd(CN run) = {bvd:.2g}, dof {bvd.df:2.1f}')
    k = GTC.ureal(k_val_mturns/1000, k_unc, 8, label='k_turns')
    print(f'k ={k} turns, dof {k.df:2.1f}')

    ratio1_2 = (N1/N2)*(1 + k*Na/N1)*(1 + bvd/I2R2)  # Uncert on I2R2??
    print(f'\nCalculated ratio {R1_name}/{R2_name} = {ratio1_2.x:.12f} +/- {ratio1_2.u:.2g}, dof {ratio1_2.df:2.1f}')

    ratio_dev_from_nom = ratio1_2 - R1_nom/R2_nom
    print(f'Ratio deviation from nominal: {ratio_dev_from_nom:.2e}, dof {ratio_dev_from_nom.df:2.1f}')

    if input('\nWrite to CCC.db database (y,n)? ') == 'y':
       db_write = True

    if db_write:
        # Write to Runs table:
        headings = 'Basename,R1_name,R1_val,R2_name,R2_val,N1,N2,Na,N_cycles,Gain,' \
                   'Delta_I2R2,k_turns,u_k,dof_k,BVD,u_BVD,dof_BVD,' \
                   'Ratio_R1_R2,u_ratio,dof_ratio,' \
                   'Dev_from_nom,u_Dev,dof_Dev'
        values = f"'{basename}','{R1_name}',{R1_nom},'{R2_name}',{R2_nom},{N1},{N2},{Na},{n},{gain:.1e}," \
                 f"{I2R2},{k.x:.5e},{k.u:.2e},{k.df},{bvd.x},{bvd.u:.2e},{bvd.df}," \
                 f"{ratio1_2.x},{ratio1_2.u:.2e},{ratio1_2.df:.1f}," \
                 f"{ratio_dev_from_nom.x:.6e},{ratio_dev_from_nom.u:.2e},{ratio_dev_from_nom.df:.1f}"
        query = f"INSERT OR REPLACE INTO Runs ({headings}) VALUES ({values});"
        curs.execute(query)
        db_connection.commit()

# ----------------run loop-----------------------

# Update database and tidy up:
if db_write:
    curs.close()
    db_connection.close()

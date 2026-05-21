"""
ccc_fns.py

Useful functions
"""
import sqlite3
import datetime as dt
import os
import statistics

DB_DIR = r'C:\Users\t.lawson\Callaghan Innovation\ORG-MSL [MSL] - ' \
         r'Electricity\Ongoing\QHR_CCC\Magnicon CCC\Measurements\CCC.db'
ROOTDATADIR = r'C:\Users\t.lawson\Callaghan Innovation\ORG-MSL [MSL] - Electricity' \
              r'\Ongoing\QHR_CCC\Magnicon CCC\Measurements\Data'
TIMEBASE = 0.02  # One 50 Hz cycle.


def present_runs():
    """
    Present all available data directories and prompt user selection;
    Present list of CN runs.
    Return dictionary of available runs and data directory path.
    """
    contents = os.listdir(ROOTDATADIR)
    print('\nAvailable data directories:')
    for item in contents:
        if '.' in item:
            continue
        print(item)
    data_dir = input('Enter directory: ')  # One day's-worth of files.
    data_path = os.path.join(ROOTDATADIR, data_dir)  # Full path to one day's-worth of files.
    data_dir_contents = os.listdir(data_path)
    r_dict = create_runtable(data_dir_contents)

    print('\nAvailable runs:')
    good_run_count = 0
    for run in r_dict.keys():
        cfgfilepath = make_full_path(data_dir, r_dict[run]['cfg_file'])
        bvdfilepath = make_full_path(data_dir, r_dict[run]['bvd_file'])
        if extract_parameter(bvdfilepath, 'bvd averages', ':').startswith('x'):
            print(f'Skipping unfinished run {run}.')
            continue  # Skip - Unfinished run
        cal_mode = extract_parameter(cfgfilepath, 'cn_calmode 3', '=')
        non_cn_mode = extract_parameter(cfgfilepath, 'cn_short 3', '=')
        n_bvd = int(extract_parameter(bvdfilepath, 'bvd averages', ':'))
        if cal_mode == 'FALSE' or non_cn_mode == 'TRUE' or n_bvd <= 1:
            continue  # Skip this file if not a CN run or calibration mode is OFF or no bvd values.
        else:
            run_num_str = run
            criteria_met_msg = f'calmode = {cal_mode}, CN mode is ON, n_bvd > 1 ({n_bvd}).'
            good_run_count += 1
        print(f'Run number {run_num_str}:\t\t{criteria_met_msg}')
    assert good_run_count > 0, 'No suitable runs available!'
    return r_dict, data_dir


def make_full_path(sub_dir, filename):
    """
    Create absolute path for sub_dir/filenmame.
    """
    return os.path.join(ROOTDATADIR, sub_dir, filename)


def get_bvd_data(path_to_file):
    bvd_vals = []
    with open(path_to_file, 'r') as bvd_file:
        line = bvd_file.readline()  # 1st line
        while line[0] != '#':  # Header line before 1st data row (on exit)
            line = bvd_file.readline()
            if line.startswith('integration time'):
                sampletime = TIMEBASE * float(line.split(':')[1].strip())  # in s
            if line.startswith('number of samples per half cycle'):
                samples_per_cycle = 2 * float(line.split(':')[1].strip())
                # cycletime = samples_per_cycle * sampletime

        while True:
            line = bvd_file.readline()  # data row
            if not line:
                break  # break at EOF
            bvd = float(line.split()[1])  # Split at " ", cast 2nd item as float
            bvd_vals.append(bvd)
    print(f'End of file - read {len(bvd_vals)} values.\n')
    return bvd_vals


def truncate(all_vals):
    """
    Truncate array 'all_vals'. Return a new array, shortened to n_keep elements.
    """
    n_keep = input("Enter cut-off point (default is to keep all points): ")
    if n_keep == "" or int(n_keep) >= len(all_vals):
        n_keep = len(all_vals)
    n_keep = int(n_keep)
    return all_vals[0:n_keep]


def mean_and_sd(vals):
    return statistics.mean(vals), statistics.stdev(vals)


def cut_outliers(vals):
    """
    Remove points that are beyond n_sd standard deviations from the mean.
    Return the thinned array, its average, outlier cut threshold and n.
    """
    av, sdev = mean_and_sd(vals)
    bvd_vals_kept = []
    n_sd = input("No. of std dev's for data cut (default is no cut): ")
    if n_sd == "":  # Default is to keep all data
        bvd_vals_kept = vals  # n_sd = 3: ~99.7% kept (if normal distribution).
        n_sd = 0
        sdn = 0
    else:
        sdn = float(n_sd)*sdev
        for val in vals:
            if (val > av + sdn) or (val < av - sdn):
                continue  # skip failed points
            bvd_vals_kept.append(val)
        print(f'mean bvd (before cut) = {av:.2e} +/- {sdev:.2e} V')
    return bvd_vals_kept, av, sdn, float(n_sd)


def extract_parameter(filepath, param, sep):
    """
    Search file filepath for param (where sep is the delimiter between param and the value)
    and return corresponding value (as a string).
    """
    with open(filepath, 'r', encoding='ansi') as file_p:
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
    Return <basename>, <date_str>, <run_num_str>, <time_str>, <filetype>
    :param file: (str) filename to parse. E.g.: 260203_001_1127.txt, 260203_001_1127_bvd, 260203_001_1127_cccdrive.cfg
    :return: dict containing above keys.
    """
    file_data = {'basename': '', 'date_str': '', 'run_num_str': '', 'time_str': '', 'type': ''}
    file_parts = file.split('_')
    file_data['basename'] = '_'.join(file_parts[:3])  # e.g. '260203_001_1127'
    if file.endswith('.txt') or file.endswith('.cfg'):
        file_data['date_str'] = file_parts[0]
        file_data['run_num_str'] = file_parts[1]
        file_data['time_str'] = file_parts[2]
        if len(file_parts) < 4:
            file_data['type'] = ''
        else:
            file_data['type'] = file_parts[3]
    return file_data


def filename_check(file):
    """
    Basic checks to confirm the filename conforms to a standard structure.
    :param file: Filename string
    :return: Boolean (True for success)
    """
    file_parts = file.split('_')
    if len(file_parts) < 3:  # Should be 3 or 4 parts
        return False
    elif len(file_parts[0]) != 6:  # Date part should be 6 digits
        return False
    elif len(file_parts[1]) != 3:  # Run-number part should be 3 digits
        return False
    elif len(file_parts[2]) < 4:  # Time part should be 4 or more characters
        return False
    else:
        return True


def parse_basename(b_name):
    """
    Extract date, time and run number from basename.
    If the basename format is invalid, return None.

    :param b_name:
    :return: (data directory, run number, time)
    """
    if filename_check(b_name):
        parts = b_name.split('_')
        date = parts[0]
        run_no = parts[1]
        time = parts[2]  # Don't really need this yet
        year = str(int(date[:2]) + 2000)
        mon = date[2:4]
        dat = date[4:]
        data_dir = '_'.join(['-'.join([year, mon, dat]), 'CCC'])
        return data_dir, run_no, time
    else:
        return None


def create_runtable(filelist):
    """
    Collate info on data files. Group by run number
    :param filelist: list of data files
    :return: dict, keyed by run_num_str.
    """
    runtable = {}
    for file in filelist:
        if filename_check(file) is False:
            continue  # Skip files with non-conforming name format
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


def db_connect():
    # Connect to CCC database:
    db_connection = sqlite3.connect(DB_DIR)
    return db_connection


def constraints_check(a, b, c):
    """
    Check run selections are appropriate for calculating a triangle closure.
    :param a: Run basename for highest-value resistors (E.g. 10k, 1k)
    :param b: Run basename for lowest-value resistors (E.g. 1k, 100)
    :param c: Run basename for highest and lowest-value resistors  (E.g. 10k, 100)
    :return: dictionary
    """
    t_fmt = '%y%m%d %H%M'
    T_DIFF_MAX = 7  # Max 1 week
    chk_dict = {'status': False,
                'fail_msg_lst': [],
                'R_high': 0, 'R_mid': 0, 'R_low': 0}

    # Check all runs are contemporary (within 1 week of each other):
    t_a = ' '.join([a.split('_')[0], a.split('_')[2]])  # E.g. '260225 0831'
    t_b = ' '.join([b.split('_')[0], b.split('_')[2]])
    t_c = ' '.join([c.split('_')[0], c.split('_')[2]])
    time_a = dt.datetime.strptime(t_a, t_fmt)
    time_b = dt.datetime.strptime(t_b, t_fmt)
    time_c = dt.datetime.strptime(t_c, t_fmt)

    earliest = min([time_a, time_b, time_c])
    latest = max([time_a, time_b, time_c])
    diff = latest - earliest
    diff_days = diff.days + diff.seconds/86400
    if diff_days > T_DIFF_MAX:
        chk_dict['fail_msg_lst'].append('>> Runs too separated in time (>1 week)!')

    # Check we have 3 different runs:
    if len(set([a, b, c])) < 3:
        chk_dict['fail_msg_lst'].append('>> Duplicated runs(s)!')

    db_connection = db_connect()
    curs = db_connection.cursor()

    query = f"SELECT R1_val, R2_val FROM Runs where Basename = '{a}';"
    curs.execute(query)
    R1_a, R2_a = curs.fetchone()  # E.g. 10k, 1k

    query = f"SELECT R1_val, R2_val FROM Runs where Basename = '{b}';"
    curs.execute(query)
    R1_b, R2_b = curs.fetchone()  # E.g. 1k, 100

    query = f"SELECT R1_val, R2_val FROM Runs where Basename = '{c}';"
    curs.execute(query)
    R1_c, R2_c = curs.fetchone()  # E.g. 10k, 100

    # Check we have 3 different resistor values:
    if len(set([R1_a, R2_a, R1_b, R2_b, R1_c, R2_c])) != 3:
        chk_dict['fail_msg_lst'].append('>> Not three unique resistors values!')
    else:
        chk_dict['R_high'] = R1_a  # or R1_c
        chk_dict['R_mid'] = R1_b  # or R2_a
        chk_dict['R_low'] = R2_b  # or R2_c

    # Check correct assignment of resistors to 'high', 'mid', 'low':
    if R1_a != R1_c or R1_b != R2_a or R2_b != R2_c:
        chk_dict['fail_msg_lst'].append('>> Wrong ratio or resistor assignments!')

    # Update check status if all good:
    if len(chk_dict['fail_msg_lst']) == 0:
        chk_dict['status'] = True

    return chk_dict

def valid_run_num(s):
    if len(s) == 3 and s.isnumeric():
        return True
    else:
        return False

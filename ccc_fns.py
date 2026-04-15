"""
ccc_fns.py

Useful functions
"""
import sqlite3
import datetime as dt

DB_DIR = r'C:\Users\t.lawson\Callaghan Innovation\ORG-MSL [MSL] - ' \
         r'Electricity\Ongoing\QHR_CCC\Magnicon CCC\Measurements\CCC.db'


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

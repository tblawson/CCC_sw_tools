"""
Log_temps.py

A script to log the temperature readings from the Lakeshore 340 temperature controller.
    Tim Lawson
    16/01/2026
"""

import datetime as dt
import time
import pyvisa as visa
import csv
import os

TIME_FMT = '%Y-%m-%d_%H%M%S'  # E.g. 2026-04-13_091411
LOGDIR = r'C:\Users\ETF\OneDrive - Callaghan Innovation\Desktop'
N_READINGS = input('Number of readings > ')  # E.g. 600
T_REPEAT = input('Delay between readings (s) > ')  # E.g. 600 seconds
RM = visa.ResourceManager()
CHANS = {'A': 0.0, 'B': 0.0, 'C1': 0.0, 'C2': 0.0}

address = 'GPIB0::12::INSTR'  # Hard-wired address for now
Lakeshore = RM.open_resource(address)

run_time_s = T_REPEAT*(T_REPEAT - 1)
print(f'Estimated run time: {run_time_s} s')

print('\nInitial test readings:')
print('Time                       \tA(K)      \tB(K)      \tC1(K)     \tC2(K)')
t_stamp = dt.datetime.now()
t_stamp_str = t_stamp.strftime(TIME_FMT)
for key in CHANS.keys():
    CHANS[key] = Lakeshore.query(f'KRDG? {key}').strip()
    #    t_stamp = dt.datetime.now()
    time.sleep(0.1)
print(f"{t_stamp}\t{CHANS['A']}\t{CHANS['B']}\t{CHANS['C1']}\t{CHANS['C2']}")

# Start logging ...
log_file = os.path.join(LOGDIR, f'T_log_{t_stamp_str}.csv')  # Unique filename, based on date & time.
with open(log_file, 'w', newline='') as T_log_file:
    T_logwriter = csv.writer(T_log_file, delimiter=',', quotechar='#', quoting=csv.QUOTE_MINIMAL)

    print('\nLOGGING START...')
    T_logwriter.writerow(['Time', 'A(K)', 'B(K)', 'C1(K)', 'C2(K)'])
    t_stamp = dt.datetime.now()
    for n in range(N_READINGS):  # E.g. 0 to 599
        for key in CHANS.keys():
            CHANS[key] = Lakeshore.query(f'KRDG? {key}').strip()
            time.sleep(0.1)
        T_logwriter.writerow([t_stamp, CHANS['A'], CHANS['B'], CHANS['C1'], CHANS['C2']])
        print(f"{t_stamp}\t{CHANS['A']}\t{CHANS['B']}\t{CHANS['C1']}\t{CHANS['C2']}")
        if n == N_READINGS-1:  # Add delay after measurement unless it's the last.
            break
        else:
            time.sleep(T_REPEAT)

print('DONE.')

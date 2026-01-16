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

RM = visa.ResourceManager()
CHANNELS = {'A': 0.0, 'B': 0.0, 'C1': 0.0, 'C2': 0.0}

instr_list = RM.list_resources()
print(f'Available GPIB devices:\n{instr_list}')
address = input('select GPIB device: ')
Lakeshore = RM.open_resource(address)

print('\nInitial test readings:\n')
for key in CHANNELS.keys():
    CHANNELS[key] = Lakeshore.query(f'KRDG? {key}')
    time.sleep(0.1)
    print(f'{key} = {CHANNELS[key]} K')

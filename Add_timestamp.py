"""
Add_timestamp.py

This script adds missing time data to the Runs table in the CCC.db database.
"""

import os
import ccc_fns as cf

# Connect to CCC database:
db_connection = cf.db_connect()
curs = db_connection.cursor()

query = "SELECT Basename FROM Runs WHERE Time is NULL;"
curs.execute(query)
rows = curs.fetchall()
basenames = [bn[0] for bn in rows]

for b_name in basenames:
    data_dir, run, t = cf.parse_basename(b_name)
    bvd_file = f'{b_name}_bvd.txt'

    datafilepath = os.path.join(cf.ROOTDATADIR, data_dir, bvd_file)
    date_str = cf.extract_parameter(datafilepath, 'start date', ':')
    time_str = cf.extract_parameter(datafilepath, 'start time', ':').replace('.', ':')
    start_datetime_str = ' '.join([date_str, time_str])
    print(f'{b_name}:\tWriting {start_datetime_str} to Runs/Time')

    query = f"UPDATE Runs SET Time = '{start_datetime_str}' WHERE Basename = '{b_name}';"
    curs.execute(query)
    db_connection.commit()

curs.close()
db_connection.close()

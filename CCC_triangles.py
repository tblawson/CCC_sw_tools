"""
CCC_triangles.py

A script to select triple-runs and calculate triangle error.
Write the result to the Triangles table and Runs_Triangles linking table in the CCC.db database.
    Tim Lawson
    16/03/2026
"""
import GTC
import ccc_fns as cf


# ----------------------MAIN SCRIPT---------------------
# Connect to CCC database:
db_connection = cf.db_connect()
curs = db_connection.cursor()

# Present run choices:
query = "SELECT DISTINCT Basename, R1_name, R2_name FROM Runs ORDER BY Basename ASC;"
curs.execute(query)
run_options = curs.fetchall()
print('\nList of runs (basename, R1_name, R2_name):')
for row in run_options:
    print(row)

# Select three runs:
# failed_checks = True
while True:  # failed_checks:
    run_a = input('\nSelect 1st run basename (LARGEST two resistors): ')
    run_b = input('Select 2nd run basename (SMALLEST two resistors): ')
    run_c = input('Select 3rd run basename (LARGEST AND SMALLEST resistors): ')
    check_dict = cf.constraints_check(run_a, run_b, run_c)
    if check_dict['status'] is True:
        # failed_checks = False
        print(f'{check_dict}\n')
        break  # Great! We're all good.
    else:  # Constraints NOT met:
        print(f"The following constraint failures were found. Please reselect runs.")
        for msg in check_dict['fail_msg_lst']:
            print(msg)
        continue

# Extract ratios:
ratios = {}
for run in [run_a, run_b, run_c]:  # E.g. '260130_004_1210'...
    query = f"SELECT Ratio_R1_R2,u_ratio,dof_ratio FROM Runs WHERE Basename = '{run}';"
    curs.execute(query)
    result = curs.fetchone()
    ratios[run] = GTC.ureal(result[0], result[1], result[2], label=run)
print(f'{ratios}\n')

# Calculate closure error:
closure = ratios[run_a]*ratios[run_b]/ratios[run_c] - 1
k = GTC.rp.k_factor(closure.df, 95)
EU = k*closure.u
print(f'Triangle closure error = {closure.x:.3e} +/- {closure.u:.3e} (dof = {closure.df:.1f}). '
      f'Exp U = {EU:.2e}, k = {k:.2f}')

# Write to db:
db_write = False  # Default behaviour is to NOT write to the database.
if input('\nWrite to CCC.db database (y,n)? ') == 'y':
    db_write = True

if db_write:
    # Triangles table first
    headings = 'Closure_err,u_Closure,dof_Closure'
    values = f'{closure.x},{closure.u},{closure.df}'
    query = f"INSERT OR REPLACE INTO Triangles ({headings}) VALUES ({values});"
    curs.execute(query)
    db_connection.commit()  # Ensure latest triangle_id is updated in database.

    # Get triangle id (this is set to AUTOINCREMENT, so largest id is the most recently-added):
    query = 'SELECT Triangle_id FROM Triangles ORDER BY Triangle_id DESC LIMIT 1;'
    curs.execute(query)
    tri_id = curs.fetchone()[0]  # This is the Triangle_id we're currently dealing with.

    # Runs_Triangles table:
    for run in [run_a, run_b, run_c]:
        headings = 'Triangle_id,Basename'
        values = f"{tri_id},'{run}'"
        query = f"INSERT OR REPLACE INTO Runs_Triangles ({headings}) VALUES ({values});"
        curs.execute(query)
    print(f'\nAdded Triangle_id {tri_id}.')

# Update database and tidy up:
if db_write:
    db_connection.commit()
    curs.close()
    db_connection.close()

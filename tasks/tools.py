import argparse
import os
import json
from tasks.meta import CurrentSession

REMOVE_FROM_DO = "removefromdo"
EXTRACT_NULLS_FROM_LOG = "nullsfromlog"
MERGE_NULLS_FILES = "mergenullsfiles"


def remove_from_do(id):
    MINIMUM_ID_LENGTH = 5
    MAX_COLS_TO_PRINT = 50

    if len(id) < MINIMUM_ID_LENGTH:
        print("The identifier '{}' is too short (minimum {} characters)".format(id, MINIMUM_ID_LENGTH))
        return

    session = CurrentSession().get()

    numtables = session.execute(
        "SELECT count(*) FROM observatory.obs_table WHERE id LIKE '{}%'"
        .format(id)).fetchone()[0]
    print(" --> This will delete {} entries from observatory.OBS_TABLE".format(numtables))
    for table in session.execute("SELECT id FROM observatory.obs_table WHERE id LIKE '{}%'".format(id)).fetchall():
        print("\t" + table[0])

    numcols = session.execute(
        "SELECT count(*) FROM observatory.obs_column WHERE id LIKE '{}%'"
        .format(id)).fetchone()[0]
    print(" --> This will delete {} entries from observatory.OBS_COLUMNS".format(numcols))
    for column in session.execute(
            "SELECT id FROM observatory.obs_column WHERE id LIKE '{}%'".format(id)).fetchmany(MAX_COLS_TO_PRINT):
        print("\t" + column[0])
    if numcols > MAX_COLS_TO_PRINT:
        print("\t... ({} more)".format(numcols - MAX_COLS_TO_PRINT))
    print(" --> This will drop {} tables from the 'observatory' schema".format(session.execute(
        "SELECT count(*) FROM observatory.obs_table WHERE id LIKE '{}%'".format(id)).fetchone()[0]))

    yn = input("Continue? (Y/N) ")

    if yn.lower() != "y":
        return

    for table in session.execute(
            "SELECT tablename FROM observatory.obs_table WHERE id LIKE '{}%'".format(id)).fetchall():
        session.execute("DROP TABLE observatory.{}".format(table[0]))
        print("Table {} dropped".format(table[0]))
    session.execute("DELETE FROM observatory.obs_table WHERE id LIKE '{}%'".format(id))
    print("Deleted {} entries from observatory.OBS_TABLE".format(numtables))
    session.execute("DELETE FROM observatory.obs_column WHERE id LIKE '{}%'".format(id))
    print("Deleted {} entries from observatory.OBS_COLUMNS".format(numcols))

    session.execute("COMMIT")


def extract_nulls_from_log(infile, outfile, relevant_fields):
    STR_NULL = 'contain only NULL values: '
    STR_ERROR = '[ERROR]'
    STR_INFO = '[INFO]'
    STR_EXCEPTIONS = 'exceptions'

    relevant_fields = relevant_fields.split(',')
    cols = {}

    try:
        os.remove(outfile)
    except OSError:
        pass

    with open(outfile, 'a') as fout, open(infile) as fin:
        current_params = {}
        for line in fin:
            if STR_ERROR in line:
                current_params = {}
                try:
                    vals = {item.split("=")[0].strip(): item.split("=")[1].strip()
                            for item in line[line.rfind('(') + 1:line.rfind(')')].split(',')}
                    current_params = {k: v for k, v in vals.items() if k in relevant_fields}
                except Exception as e:
                    pass

            elif STR_NULL in line and STR_INFO not in line:
                columns = [x.strip() for x in line[line.rfind(STR_NULL) + len(STR_NULL):].split(',')]

                for column in columns:
                    if column in cols:
                        if current_params not in cols[column][STR_EXCEPTIONS]:
                            cols[column][STR_EXCEPTIONS].append(current_params)
                    else:
                        cols[column] = {}
                        cols[column][STR_EXCEPTIONS] = [current_params]

        fout.write(json.dumps(cols, indent=4))

    print(' >>>---> Done! Written file {}'.format(outfile))


def merge_nulls_files(infile1, infile2, outfile):
    STR_EXCEPTIONS = 'exceptions'

    try:
        os.remove(outfile)
    except OSError:
        pass

    with open(outfile, 'a') as fout, open(infile1) as fin1, open(infile2) as fin2:
        json1 = json.load(fin1)
        json2 = json.load(fin2)

        for column in set(list(json1.keys()) + list(json2.keys())):
            col1 = json1.get(column, json1.get(column.lower(), {})).get(STR_EXCEPTIONS, [])
            col2 = json2.get(column, json2.get(column.lower(), {})).get(STR_EXCEPTIONS, [])

            json1[column][STR_EXCEPTIONS] = col1 + [x for x in col2 if x not in col1]

        fout.write(json.dumps(json1, indent=4))

    print(' >>>---> Done! Merged {} and {} into {}'.format(infile1, infile2, outfile))


if __name__ == "__main__":
    parser = argparse.ArgumentParser('python tools.py')
    parser.add_argument('task', help='Task to be executed')
    parser.add_argument('task_parameters', nargs='+', help='Task parameters')
    args = vars(parser.parse_args())
    if args['task'].lower() == REMOVE_FROM_DO and len(args['task_parameters']) == 1:
        remove_from_do(args['task_parameters'][0])
    elif args['task'].lower() == EXTRACT_NULLS_FROM_LOG:
        if len(args['task_parameters']) == 3:
            extract_nulls_from_log(args['task_parameters'][0], args['task_parameters'][1], args['task_parameters'][2])
        else:
            print('usage: python tools.py nullsfromlog file_in file_out relevant,fields,comma,separated')
    elif args['task'].lower() == MERGE_NULLS_FILES:
        if len(args['task_parameters']) == 3:
            merge_nulls_files(args['task_parameters'][0], args['task_parameters'][1], args['task_parameters'][2])
        else:
            print('usage: python tools.py mergenullsfiles file_in1 file_in2 file_out')
    else:
        parser.print_help()

import csv
import os.path

from common import *

boards = Leaderboards()

for when, board_url, board_entries in boards.query_dailies():
    path = 'raw/daily_%s.csv' % when.strftime('%Y_%m_%d')

    refresh = True

    if os.path.exists(path):
        csv_entries = len(list(file(path, 'r'))) - 1

        if csv_entries == board_entries:
            print 'Skipping downloaded board: %s' % path
            refresh = False
        else:
            print 'Refreshing updated board (old = %d, new = %d): %s' % (csv_entries, board_entries, path)
    else:
        print 'Downloading missing board: %s' % path

    if refresh:
        recs = download_daily(board_url)

        rows = []
        rows.append(ENTRY_FIELDS)
        for rec in recs:
            row = []
            for f in ENTRY_FIELDS:
                row.append(rec[f])
            rows.append(row)

        wr = csv.writer(file(path, 'w'))
        for row in rows:
            wr.writerow(row)

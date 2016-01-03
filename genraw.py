import csv
import os.path

from common import *

boards = Leaderboards()

for when, board_url in boards.query_dailies():
    path = 'raw/daily_%s.csv' % when.strftime('%Y_%m_%d')

    if os.path.exists(path):
        print 'Skipping downloaded board: %s' % path
    else:
        print 'Downloading missing board: %s' % path
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

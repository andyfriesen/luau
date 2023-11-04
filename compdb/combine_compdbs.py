#!/usr/bin/env python3

import sys
import argparse
import json

parser = argparse.ArgumentParser()

parser.add_argument("database", nargs='+')
parser.add_argument('--output', '-o', dest='output', required=True)

def main(argv):
    args = parser.parse_args(argv)

    result = {}

    for fn in args.database:
        content = json.load(open(fn, 'r'))

        for row in content:
            result[row['file']] = row

    res = list(result.values())

    json.dump(res, open(args.output, 'w'), indent = 4)

if __name__ == '__main__':
    main(sys.argv[1:])

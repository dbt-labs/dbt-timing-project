import argparse
import datetime
from functools import reduce
import git
from math import ceil
import os
import subprocess
from shutil import rmtree
from statistics import mean, median
import sys
import time
from time import perf_counter


# overrides error behavior for arg parser
class MyParser(argparse.ArgumentParser):
    def error(self, message):
        sys.stderr.write('error: %s\n' % message)
        self.print_help()
        sys.exit(2)

def create_if_doesnt_exist(path):
    if not os.path.exists(path):
        os.mkdir(path)

def remove_and_recreate_dir(path):
    if os.path.exists(path):
        rmtree(path)
        os.mkdir(path)
    else:
        os.mkdir(path)

def remove_if_exists(path):
    if os.path.exists(path):
        os.remove(path)

# returns None if there was an error
def parse_args():
    parser = MyParser(description='Benchmark two dbt branches')
    parser.add_argument(
        '--cached',
        '-c',
        action='store_true',
        help="skips git clone and install steps."
    )
    parser.add_argument(
        '--runs',
        type=int,
        default=10,
        dest='runs',
        help="number of runs to test for each branch. defaults to 10."
    )
    parser.add_argument(
        'dev',
        type=str,
        help='branch with changes to benchmark'
    )
    parser.add_argument(
        'base',
        type=str,
        help='branch to compare against. typically "develop"'
    )
    return parser.parse_args()

def path_from(dir_list):
    return './' + '/'.join(dir_list)

# returns the time to evaluate the thunk in seconds
def time(thunk):
    start = perf_counter()
    thunk()
    stop = perf_counter()
    return round(stop - start, 3)

# returns the percentage faster
def improvement(base, better):
    return 100 * ((base - better) / base)

def print_results(kvs):
    def pair_to_line(padding_char, kv):
        if kv[1] is None:
            padding_size = ceil((full_width - len(kv[0])) / 2)
            padding = ''.join([padding_char] * (padding_size))
            return padding + kv[0] + padding
        else:
            padding = ''.join([padding_char] * (full_width - len(kv[0]) - len(kv[1])))
            return kv[0] + padding + kv[1]

    def padding_char_from_value(v):
        if v is None:
            return ' '
        else:
            return '.'
    
    # measure the length of None as zero
    def len_none_is_zero(x):
        if x is None:
            return 0
        else:
            return len(x)

    # if value is none, don't measure the width of the key
    def key_len_of_non_none_values(kv): 
        if kv[1] is None:
            return 0
        else:
            return len(kv[0])

    max_key_width = reduce(lambda x,y: max(x, key_len_of_non_none_values(y)), kvs, 0)
    max_value_width = reduce(lambda x,y: max(x, len_none_is_zero(y[1])), kvs, 0)
    # extra added defines minimum separator width
    full_width = max_key_width + max_value_width + 4

    # create list of lines to print
    header = pair_to_line(':', ('  Benchmark stats  ', None))
    lines = [header] + list(map(lambda pair: pair_to_line(padding_char_from_value(pair[1]), pair), kvs))
    
    # print all the lines
    for line in lines:
        print(line)


# creates lines for a single stat
def get_stat(name, dev, base):
    percent = round(improvement(base, dev), 2)

    lines = [
        (f"{name} dev", f"{dev}"),
        (f"{name} base", f"{base}")
    ]

    if percent > 0:
        return lines + [('IMPROVED BY', f"{percent} "), ("", None)]
    else:
        return lines + [('DEGRADED BY', f"{abs(percent)} %"), ("", None)]

def gather_output(args, dev, base):
    # mutably sort by reference
    dev.sort()
    base.sort()

    # return the list of lines
    return [
        ('command', 'dbt parse'),
        ('dev branch', f"dbt/{args.dev}"),
        ('base branch', f"dbt/{args.base}"),
        ('', None),
        ('time measured in seconds', None),
        ('', None) 
    ] \
        + get_stat('mean', round(mean(dev), 2), round(mean(base), 2)) \
        + get_stat('median', round(median(dev), 2), round(median(base), 2))

def subprocess_with_errs(cmd):
    subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True)

def log(msg):
    ts = datetime.datetime.now().strftime('%H:%M:%S')
    print(f"{ts}  {msg}")

class Branch():
    def __init__(self, name, setup_thunk, run_thunk, cleanup_thunk, time_remaining):
        self.name = name
        self.setup_thunk = setup_thunk
        self.run_thunk = run_thunk
        self.cleanup_thunk = cleanup_thunk
        self.time_remaining = time_remaining
        self.runs = []

    def run_branch(self, args):
        log(f"running {self.name} branch setup")
        self.setup_thunk()
        # mean and median thow on empty list inputs
        # to speed up development time, allow empty runs as a special case.
        if args.runs < 1:
            self.runs = [1.0] * 10
            self.runs = [1.0] * 10
        # complete the runs (this is what takes so long)
        else:
            for thunk in ([self.run_thunk] * args.runs):
                log(f"dev run {len(self.runs) + 1}/{args.runs}")
                run = time(thunk)
                self.runs = self.runs + [run]
                remaining = self.time_remaining(self.runs, args.runs)
                log(f"run completed in {run} seconds")
                log(f"estimated time remaining: {remaining} seconds")
                log(f"running {self.name} cleanup")
                self.cleanup_thunk()

def main():
    # parse command line arguments
    # exits on error
    args = parse_args()

    # print title
    print()
    print(':::: Benchmark.py ::::')

    # directory names
    workspace_dir = 'target'
    dev_dir = 'dev'
    base_dir = 'base'

    # generated path strings from above directory names
    workspace_path = path_from([workspace_dir])
    dev_path = path_from([workspace_dir, dev_dir])
    base_path = path_from([workspace_dir, base_dir])
    # not using workspace dir because `target` is dbt-specific
    partial_parse_path = path_from(['target', 'partial_parse.pickle'])

    # value that defines dev branch benchmark behavior
    dev = Branch(
        name='dev',
        setup_thunk=lambda : remove_if_exists(partial_parse_path),
        run_thunk=lambda : subprocess_with_errs(f"cd {dev_path} && source env/bin/activate && cd ../.. && dbt parse"),
        cleanup_thunk=lambda : remove_if_exists(partial_parse_path),
        time_remaining=lambda l,n : int(round(mean(l) * ((2 * n) - len(l)), 0))
    )

    # value that defines base branch benchmark behavior
    base = Branch(
        name='base',
        setup_thunk=lambda : remove_if_exists(partial_parse_path),
        run_thunk=lambda : subprocess_with_errs(f"cd {base_path} && source env/bin/activate && cd ../.. && dbt parse"),
        cleanup_thunk=lambda : remove_if_exists(partial_parse_path),
        time_remaining=lambda l,n : int(round(mean(l) * (n - len(l)), 0))
    )

    if not args.cached:
        log('setting up directories') 

        # set up workspace directories
        create_if_doesnt_exist(workspace_path)
        remove_and_recreate_dir(dev_path)
        remove_and_recreate_dir(base_path)

        log('cloning both branches with local identity')
        log('may ask for ssh password twice (once for each branch)')

        # clone branches
        git.Repo.clone_from(
            'git@github.com:fishtown-analytics/dbt',
            dev_path,
            branch=args.dev
        )
        git.Repo.clone_from(
            'git@github.com:fishtown-analytics/dbt',
            base_path,
            branch=args.base
        )

        # create virtual environments
        subprocess_with_errs(f"cd {dev_path} && python3 -m venv env")
        subprocess_with_errs(f"cd {base_path} && python3 -m venv env")

        # upgrade pip
        subprocess_with_errs(f"cd {dev_path} && source env/bin/activate && pip install --upgrade pip")
        subprocess_with_errs(f"cd {base_path} && source env/bin/activate && pip install --upgrade pip")
        
        # install branches
        log('installing dev branch')
        subprocess_with_errs(f"cd {dev_path} && source env/bin/activate && pip install -r requirements.txt -r dev_requirements.txt")
        log('installing base branch')
        subprocess_with_errs(f"cd {base_path} && source env/bin/activate && pip install -r requirements.txt -r dev_requirements.txt")
    
    # run benchmarks. This takes a long time.
    dev.run_branch(args)
    base.run_branch(args)
    
    # output timer information and comparison math.
    print()
    print_results(gather_output(args, dev.runs, base.runs))

    # print raw runtimes
    print(f"raw dev_runs:  {dev.runs}")
    print(f"raw base_runs: {base.runs}")
    print()
 

if __name__ == '__main__':
    main()
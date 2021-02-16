import argparse
from functools import reduce
import git
import os
from shutil import rmtree
from statistics import mean, median
import sys
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
        'command',
        type=str,
        help='specifies the dbt command to benchmark. run as `dbt <command>`.'
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

# prints the block for a single stat
def print_stat(name, dev, base):
    percent = round(improvement(base, dev), 2)

    print(f'{name} dev:    {dev}')
    print(f'{name} base:   {base}')
    if percent > 0:
        print(f'IMPROVED BY: {percent}%')
    else:
        print(f'DEGRADED BY: {abs(percent)}%')
    print()

def print_results(args, dev, base):
    # mutably sort
    dev.sort()
    base.sort()

    # print all the stats
    print()
    print('::::::  Benchmark stats  ::::::')
    print(f"command:     dbt {args.command}")
    print(f"dev branch:  dbt/{args.dev}")
    print(f"base branch: dbt/{args.base}")
    print(' - absolute times in seconds - ')
    print()
    print(f"raw data: dev_runs: {dev}")
    print(f"raw data: base_runs: {base}")
    print()
    print_stat('mean', mean(dev), mean(base))
    print_stat('median', median(dev), median(base))

def main():
    # parse command line arguments
    # exits on error
    args = parse_args()

    # exit if less than one run requested
    # (mean and median will throw on empty list inputs)
    if args.runs < 1:
        print('benchmark.py: must have at least one run')
        return

    print(args)

    # directory names
    workspace_dir = 'target'
    dev_dir = 'dev'
    base_dir = 'base'

    # generated path strings from above directory names
    workspace_path = path_from([workspace_dir])
    dev_path = path_from([workspace_dir, dev_dir])
    base_path = path_from([workspace_dir, base_dir])

    if not args.cached:
        print('benchmark.py: setting up directories') 

        # set up workspace directories
        create_if_doesnt_exist(workspace_path)
        remove_and_recreate_dir(dev_path)
        remove_and_recreate_dir(base_path)

        print('benchmark.py: cloning both branches with local identity')
        print('benchmark.py: may ask for ssh password twice (once for each branch)')

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
        os.system(f"cd {dev_path} && python3 -m venv env")
        os.system(f"cd {base_path} && python3 -m venv env")

    # upgrade pip and install branches
    if not args.cached:
        # upgrade pip
        os.system(f"cd {dev_path} && source env/bin/activate && pip install --upgrade pip")
        os.system(f"cd {base_path} && source env/bin/activate && pip install --upgrade pip")
        
        # install branches
        print('benchmark.py: installing dev branch')
        os.system(f"cd {dev_path} && source env/bin/activate && pip install -r requirements.txt -r dev_requirements.txt")
        print('benchmark.py: installing base branch')
        os.system(f"cd {base_path} && source env/bin/activate && pip install -r requirements.txt -r dev_requirements.txt")
    
    # define thunks that run the dbt command when evaluated
    dev_thunk = lambda : os.system(f"cd {dev_path} && source env/bin/activate && cd ../.. && dbt {args.command}")
    base_thunk = lambda : os.system(f"cd {base_path} && source env/bin/activate && cd ../.. && dbt {args.command}")

    # complete the runs (this is what takes so long)
    print('benchmark.py: running dev branch')
    dev_runs = list(map(time, [dev_thunk] * args.runs))
    print('benchmark.py: running base branch')
    base_runs = list(map(time, [base_thunk] * args.runs))
    
    # output timer information and comparison math.
    print_results(args, dev_runs, base_runs)
 

if __name__ == '__main__':
    main()
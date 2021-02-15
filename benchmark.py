from functools import reduce
import git
import os
from shutil import rmtree
from statistics import mean, median
import sys
from time import perf_counter

HELP = """
Usage:

# Shows how much faster `dbt parse` dbt/my-dev-branch is compared to dbt/develop
benchmark parse my-dev-branch

# Shows how much faster `dbt parse` dbt/my-dev-branch is compared to dbt/other-branch
benchmark parse my-dev-branch other-branch
"""
def create_if_doesnt_exist(path):
    if not os.path.exists(path):
        os.mkdir(path)

def remove_and_recreate_dir(path):
    rmtree(path)
    os.mkdir(path)

# returns None if there was an error
def parse_args(arg_list):
    arg_len = len(sys.argv) - 1 # remove the program name from arg length
    if any(map(lambda x: x in ['--help', '-h'], sys.argv)):
        print(HELP)
        return None
    elif arg_len < 2 or arg_len > 3:
        print('error: requries 2 or 3 args')
        print(HELP)
        return None
    else:
        if arg_len == 2:
            base = 'develop'
        else:
            base = sys.argv[3]
        return {'cmd': sys.argv[1], 'dev': sys.argv[2], 'base': base}

def path_from(dir_list):
    return './' + '/'.join(dir_list)

# returns the time to evaluate the thunk in microseconds
def time(thunk):
    start = perf_counter()
    thunk()
    stop = perf_counter()
    return stop - start

# returns the percentage faster
def improvement(base, better):
    100 * ((base - better) / base)

# prints the block for a single stat
def print_stat(name, dev, base):
    percent = improvement(base, dev)
    print(f'{name} dev:    {mean_dev}')
    print(f'{name} base:   {mean_base}')
    if percent > 0:
        print(f'IMPROVED BY: {percent}%')
    else:
        print(f'DEGRADED BY: {abs(percent)}%')
    print()

def remove_first_and_last_immutable(list):
    # avoid list mutation by reference
    list_copied = list.copy()
    list_copied.pop(0)
    list_copied.pop()
    return list_copied

def print_results(args, dev, base):
    # remove outliers
    dev_no_outliers = remove_first_and_last_immutable(dev)
    base_no_outliers = remove_first_and_last_immutable(base)

    # print all the stats
    print()
    print('::::::  Benchmark stats  ::::::')
    print(f"command:     dbt {args['cmd']}")
    print(f"dev branch:  dbt/{args['dev']}")
    print(f"base branch: dbt/{args['base']}")
    print(' -  absolute time in micros  - ')
    print()
    print_stat('mean', mean(dev), mean(base))
    print_stat('median', median(dev), median(base))
    print_stat('mean without outliers', mean(dev_sorted), mean(base_sorted))
    print_stat('median without outliers', median(dev_sorted), median(base_sorted))

def main():
    # parse command line arguments
    args = parse_args(sys.argv)
    # exit if the args weren't parsed
    if args is None:
        return

    # hard coding number of runs to compare
    # using an odd number for median stat
    args['runs'] = 3

    print('benchmark.py: setting up directories') 

    # directory names
    workspace_dir = 'target'
    dev_dir = 'dev'
    base_dir = 'base'

    # generated path strings from above directory names
    workspace_path = path_from([workspace_dir])
    dev_path = path_from([workspace_dir, dev_dir])
    base_path = path_from([workspace_dir, base_dir])

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
        branch=args['dev']
    )
    git.Repo.clone_from(
        'git@github.com:fishtown-analytics/dbt',
        base_path,
        branch=args['base']
    )

    # create virtual environments
    os.system(f"cd {dev_path} && python3 -m venv env")
    os.system(f"cd {base_path} && python3 -m venv env")

    ### Run Dev ###
    print('benchmark.py: installing and running dev branch')
    # install branch
    os.system(f"cd {dev_path} && source env/bin/activate && pip install -r requirements.txt -r dev_requirements.txt")
    
    # define thunks that run the dbt command when evaluated
    dev_thunk = lambda : os.system(f"dbt {args['cmd']}")

    # complete the runs (this is what takes so long)
    dev_runs = list(map(time, [dev_thunk] * args['runs']))

    # deactivate virtual environment
    os.system('deactivate')
    ### End Dev ###

    ### Run Base ###
    print('benchmark.py: installing and running base branch')
    # install branch
    os.system(f"cd {base_path} && source env/bin/activate && pip install -r requirements.txt -r dev_requirements.txt")

    # define thunks that run the dbt command when evaluated
    base_thunk = lambda : os.system(f"dbt {args['cmd']}")

    # complete the runs (this is what takes so long)
    base_runs = list(map(time, [base_thunk] * args['runs']))

    # deactivate virtual environment
    os.system('deactivate')
    ### End Base ###

    # output timer information and comparison math.
    print_results(args, dev_runs, base_runs)
 

if __name__ == '__main__':
    main()
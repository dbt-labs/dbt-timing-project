from functools import reduce
import git
import os
from shutil import rmtree
from statistics import mean, median
import sys
from time import perf_counter

HELP = """
Usage:

# Shows how much faster `dbt parse` on dbt/my-dev-branch is compared to dbt/other-branch
benchmark parse my-dev-branch other-branch

# If you want to rerun and skip the install steps
benchmark --cached parse my-dev-branch other-branch
"""

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
def parse_args(arg_list):
    arg_len = len(sys.argv) - 1 # remove the program name from arg length
    if any(map(lambda x: x in ['--help', '-h'], sys.argv)):
        print(HELP)
        return None
    elif arg_len < 3 or arg_len > 4:
        print('error: requries 3 or 4 args')
        print(HELP)
        return None
    elif arg_len == 4 and sys.argv[1] != '--cached':
        print('unexpected first argument. did you mean `--cached` ?')
        print(HELP)
        return None
    elif arg_len == 3 and sys.argv[1] == '--cached':
        print('not enough arguments after `--cached`.')
        print(HELP)
        return None
    elif arg_len == 4 and sys.argv[1] == '--cached':
        return {'cached': True, 'cmd': sys.argv[2], 'dev': sys.argv[3], 'base': sys.argv[4]}
    elif arg_len == 3 and sys.argv[1] != '--cached':
        return {'cached': False, 'cmd': sys.argv[1], 'dev': sys.argv[2], 'base': sys.argv[3]}

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
    print(f"command:     dbt {args['cmd']}")
    print(f"dev branch:  dbt/{args['dev']}")
    print(f"base branch: dbt/{args['base']}")
    print(' - absolute times in seconds - ')
    print()
    print(f"raw data: dev_runs: {dev}")
    print(f"raw data: base_runs: {base}")
    print()
    print_stat('mean', mean(dev), mean(base))
    print_stat('median', median(dev), median(base))

def main():
    # parse command line arguments
    args = parse_args(sys.argv)
    # exit if the args weren't parsed
    if args is None:
        return

    # hard coding number of runs to compare
    # numbers less than 0 behave like zero
    args['runs'] = 10

    # directory names
    workspace_dir = 'target'
    dev_dir = 'dev'
    base_dir = 'base'

    # generated path strings from above directory names
    workspace_path = path_from([workspace_dir])
    dev_path = path_from([workspace_dir, dev_dir])
    base_path = path_from([workspace_dir, base_dir])

    if not args['cached']:
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

    # upgrade pip and install branches
    if not args['cached']:
        # upgrade pip
        os.system(f"cd {dev_path} && source env/bin/activate && pip install --upgrade pip")
        os.system(f"cd {base_path} && source env/bin/activate && pip install --upgrade pip")
        
        # install branches
        print('benchmark.py: installing dev branch')
        os.system(f"cd {dev_path} && source env/bin/activate && pip install -r requirements.txt -r dev_requirements.txt")
        print('benchmark.py: installing base branch')
        os.system(f"cd {base_path} && source env/bin/activate && pip install -r requirements.txt -r dev_requirements.txt")
    
    # define thunks that run the dbt command when evaluated
    dev_thunk = lambda : os.system(f"cd {dev_path} && source env/bin/activate && cd ../.. && dbt {args['cmd']}")
    base_thunk = lambda : os.system(f"cd {base_path} && source env/bin/activate && cd ../.. && dbt {args['cmd']}")

    # complete the runs (this is what takes so long)
    print('benchmark.py: running dev branch')
    dev_runs = list(map(time, [dev_thunk] * args['runs']))
    print('benchmark.py: running base branch')
    base_runs = list(map(time, [base_thunk] * args['runs']))
    
    # output timer information and comparison math.
    print_results(args, dev_runs, base_runs)
 

if __name__ == '__main__':
    main()
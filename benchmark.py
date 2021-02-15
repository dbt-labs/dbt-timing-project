from functools import reduce
import os
import sys

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

# returns None if there was an error
def parse_args(arg_list):
    arg_len = len(sys.argv) - 1 # remove the program name from arg length
    if any(map(lambda x: x in ['--help', '-h'], sys.argv)):
        print(HELP)
        return None
    elif arg_len < 2 or arg_len > 3:
        print("error: requries 2 or 3 args")
        print(HELP)
        return None
    else:
        return {'cmd': sys.argv[1], 'dev': sys.argv[2], 'base': sys.argv[3]}

def path_from(dir_list):
    return './' + '/'.join(dir_list)

def main():
    # parse command line arguments
    args = parse_args(sys.argv)
    # exit if the args weren't parsed
    if args is None:
        return

    # variables for working directories
    workspace_path = './target'
    dev_dir = 'dev'
    base_dir = 'base'

    # create workspace directories
    create_if_doesnt_exist(path_from([workspace_path]))
    create_if_doesnt_exist(path_from([workspace_path, dev_dir]))
    create_if_doesnt_exist(path_from([workspace_path, base_dir]))
 

if __name__ == "__main__":
    main()

### dbt timing project
This repository contains command line tools to locally generate arbitrarily-sized projects and to compare benchmarks of `dbt parse` as seen in public github branches.

## Example Output

![](./screenshots/benchmark-screenshot.png)

## Installation

```
pip install -r requirements.txt
```

## Usage

1. generate dbt project files
2. run benchmark.py

```
> python3 gen_files.py --help
usage: gen_files.py [-h] files

Generate a dbt project

positional arguments:
  files       specifies the number of files to be generated in the project

optional arguments:
  -h, --help  show this help message and exit
```

```
> python3 benchmark.py --help 
usage: benchmark.py [-h] [--cached] [--runs RUNS] dev base

Benchmark two dbt branches

positional arguments:
  dev           branch with changes to benchmark
  base          branch to compare against. typically "develop"

optional arguments:
  -h, --help    show this help message and exit
  --cached, -c  skips git clone and install steps.
  --runs RUNS   number of runs to test for each branch. defaults to 10.
```

## Examples

benchmark `dbt parse` on a small project:

```
python3 gen_files.py 10
python3 benchmark.py my-branch develop
```

re-run the same benchmark with 25 runs on each branch:

```
python3 benchmark.py --cached --runs=25 my-branch develop
```

to benchmark large projects generate ~2000 files.

## Future Improvements
- right now only the `dbt parse` command is supported. the project could be abstracted further to allow for abritrary commands to be benchmarked. a config file outlining instructions for installation, setup, running, and cleanup would be necessary.
- when using `--cached` the last two parameters do nothing but are still required. it should check that those names match the cloned repositories.
- add an additional flag `--partial` that benchmarks partial tests. It will do a pre-run to generate the partial parse file then measure the runs from there without deleting the file
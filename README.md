
### dbt timing project
This repository contains scripts to generate arbitrarily-sized projects and to benchmark the speed of dbt commands by branch.


## Usage

To generate files:

```
python3 gen_files.py <number of files>
```

example for a very large project:
```
python3 gen_files.py 2000
```

To benchmark branches:
You must first generate the size project you would like to benchmark against.
```
python3 gen_files.py 2000
python3 benchmark.py my-branch-name develop
```

If you've already run the benchmark and would like to run it again without re-cloning the branches and installing use the `--cached` option:
```
python3 benchmark.py --cached my-branch-name develop
```


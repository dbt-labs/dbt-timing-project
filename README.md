
### dbt timing project
Creates a project with the specified number of models and tests. Intended for performance testing dbt core.

## Usage
```
python3 gen_files.py <graph-size>
```

for small projects consider 
```
python3 gen_files.py 100
```

for large projects consider
```
python3 gen_files.py 2000
```
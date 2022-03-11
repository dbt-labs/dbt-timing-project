#!/usr/bin/env python
import sys

import networkx as nx
import yaml
import os
import argparse
import random


# overrides error behavior for arg parser
class MyParser(argparse.ArgumentParser):
    def error(self, message):
        sys.stderr.write('error: %s\n' % message)
        self.print_help()
        sys.exit(2)

def gen_name(i):
    return "node_{}".format(i)
    
def gen_noisy_name(i):
    return "noisy_node_{}".format(i)

def gen_schema(node_name):
    return {
        "version": 2,
        "models": [
            {
                "name": node_name,
                "columns": [
                    {
                        "name": "id",
                        "tests": [
                            "unique",
                            "not_null",
                            {
                                "relationships": {
                                    "to": "ref('node_0')",
                                    "field": "id"
                                }
                            }
                        ]
                    }
                ]
            }
        ]
    }

def gen_config(noisy=False):
    from random import randrange
    db_rng = randrange(5)
    schema_rng = randrange(db_rng + (3 if noisy else 1))
    
    enabled = "var('add_noise', False)" if noisy else "True"
    database = f"('bigdb{db_rng}' if target.type in ('snowflake', 'bigquery') else target.get('database'))"
    schema = f"bigschema{schema_rng}"
    rand_mat = "view" if randrange(2) == 0 else "table"
    
    config = f"""
    config(
        enabled={enabled},
        database={database},
        schema='{schema}',
        materialized='{rand_mat}',
        file_format='delta'
    )
    """
    wrapped = "{{" + config + "}}"
    return wrapped


def gen_sql(edges=None, noisy=False):
    config = gen_config(noisy)
    contents = f"""
    {config}
    
    select 1 as fun, 'blue' as hue, true as is_cool, '2022-01-01' as date_day
    """
    if edges:
        for _, edge_id in edges:
            edge_name = gen_name(edge_id)
            contents += "\nunion all\n"
            contents += "select * from {{ ref('" + edge_name + "') }}"
    return contents


def main():
    parser = MyParser(description='Generate a dbt project')
    parser.add_argument(
        'files',
        type=int,
        help='specifies the number of files to be generated in the project'
    )
    args = parser.parse_args()
    GRAPH_SIZE = args.files

    print(":: Generating Files ::")

    G = nx.gnc_graph(GRAPH_SIZE, seed=526)
    for node_id, node in G.nodes.items():
        node_name = gen_name(node_id)

        schema = gen_schema(node_name)
        contents = gen_sql(G.edges(node_id))
        path_dir = "path_{}".format(node_id // 10)
        path = "models/{}/{}.{}"
        model_path = path.format(path_dir, node_name, 'sql')
        test_path = path.format(path_dir, node_name, 'yml')

        try:
            os.makedirs("models/{}".format(path_dir))
        except FileExistsError:
            pass

        with open(model_path, 'w') as fh:
            fh.write(contents)

        with open(test_path, 'w') as fh:
            fh.write(yaml.dump(schema))

    # create noisy objects in the same database locations
    for noisy_id in range(GRAPH_SIZE):
        noisy_name = gen_noisy_name(noisy_id)
        contents = gen_sql(noisy=True)
        path_dir = "noisy_path_{}".format(noisy_id // 10)
        path = "models/{}/{}.{}"
        model_path = path.format(path_dir, noisy_name, 'sql')
    
        try:
            os.makedirs("models/{}".format(path_dir))
        except FileExistsError:
            pass

        with open(model_path, 'w') as fh:
            fh.write(contents)

        with open(test_path, 'w') as fh:
            fh.write(yaml.dump(schema))
        

    print("Done.")
    print()

if __name__ == "__main__":
    main()

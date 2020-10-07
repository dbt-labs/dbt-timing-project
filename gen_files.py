#!/usr/bin/env python

GRAPH_SIZE = 100

import networkx as nx
import yaml
import os

def gen_name(i):
    return "node_{}".format(i)

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
                                    "from": "id",
                                    "to": "node_0",
                                    "field": "id"
                                }
                            }
                        ]
                    }
                ]
            }
        ]
    }

def gen_sql(edges):
    contents = "select 1 as id"
    for _, edge_id in edges:
        edge_name = gen_name(edge_id)
        contents += "\nunion all\n"
        contents += "select * from {{ ref('" + edge_name + "') }}"
    return contents


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

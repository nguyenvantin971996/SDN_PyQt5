from DijkstraAlgorithm import DijkstraAlgorithm
import copy
from decimal import Decimal

class Solution:
    def __init__(self):
        self.path = []
        self.length = 0

class YenAlgorithm:
    def __init__(self, weight_map, src, dst, K, same_cost=False):
        self.weight_map = weight_map
        self.src = src
        self.dst = dst
        self.K = K
        self.same_cost = same_cost

    def compute_shortest_paths(self):
        paths = []
        alg = DijkstraAlgorithm(self.weight_map)
        first_path = Solution()
        first_path.path = alg.compute_shortest_path(self.src, self.dst)
        first_path.length = self.compute_path_length(first_path.path)
        paths.append(first_path)
        if len(first_path.path) == 0:
            return [], [], []
        
        base_cost = first_path.length if self.same_cost else None
        
        B = []
        for k in range(1, self.K):
            for i in range(len(paths[-1].path) - 1):
                spurNode = paths[-1].path[i]
                rootPath = paths[-1].path[:i + 1]

                weight = copy.deepcopy(self.weight_map)
                for path in paths:
                    if rootPath == path.path[:i + 1]:
                        u, v = path.path[i], path.path[i + 1]
                        if u in weight and v in weight[u]:
                            del weight[u][v]
                        # if v in weight and u in weight[v]:
                        #     del weight[v][u]

                for j in range(i):
                    node = rootPath[j]
                    if node in weight:
                        del weight[node]
                    # for connected_node in list(weight.get(node, [])):
                    #     del weight[node][connected_node]
                    #     if connected_node in weight:
                    #         del weight[connected_node][node]

                alg_d = DijkstraAlgorithm(weight)
                spurPath = alg_d.compute_shortest_path(spurNode, self.dst)

                if spurPath:
                    totalPath = rootPath[:-1] + spurPath
                    path = Solution()
                    path.path = totalPath
                    path.length = self.compute_path_length(totalPath)
                    if not self.same_cost or path.length == base_cost:
                        dk = True
                        for path_b in B:
                            if path_b.path == path.path:
                                dk = False
                        if dk:
                            B.append(path)

            if not B:
                break

            B = sorted(B, key=lambda x: x.length)
            paths.append(B[0])
            B.pop(0)

        paths_vertices = [p.path for p in paths]
        paths_edges = [self.compute_edges_of_path(p.path) for p in paths]
        paths_length = [p.length for p in paths]
        return paths_vertices, paths_edges, paths_length

    def compute_edges_of_path(self, path):
        return [(path[i], path[i + 1]) for i in range(len(path) - 1)]

    def compute_path_length(self, path):
        length = 0
        for i in range(len(path) - 1):
            u, v = path[i], path[i + 1]
            length += self.weight_map[u][v]
        return float(length)


# import numpy as np
# values = [0,0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9,1]
# # values = [0,1,2,3,4,5,6,7,8,9,10]
# weight_map={
#     1:{2:None,3:None},
#     2:{1:None,4:None,6:None},
#     3:{1:None,4:None,7:None},
#     4:{2:None,3:None,5:None},
#     5:{4:None,6:None,7:None},
#     6:{2:None,5:None,8:None},
#     7:{3:None,5:None,8:None},
#     8:{6:None,7:None}
# }
# for node_1 in weight_map.keys():
#     for node_2 in weight_map[node_1].keys():
#         # if weight_map[node_2][node_1] != None:
#         #     weight_map[node_1][node_2] = weight_map[node_2][node_1]
#         # else:
#         weight_map[node_1][node_2] = 1
# alg = YenAlgorithm(weight_map, 1, 8, 4, same_cost=True)
# paths_vertices, paths_edges, paths_length = alg.compute_shortest_paths()
# print(paths_vertices, paths_length)

# import networkx as nx
# from itertools import islice


# # Create a graph
# G = nx.DiGraph()

# # Add edges to the graph
# for node, edges in weight_map.items():
#     for adjacent_node in edges:
#         G.add_edge(node, adjacent_node, weight=weight_map[node][adjacent_node])  # Assuming unweighted edges

# # Define the source and target
# source = 1
# target = 8

# # Number of shortest paths to find
# K = 4

# # Find the K shortest paths
# shortest_paths = nx.shortest_simple_paths(G, source, target)

# # Print the paths
# print(shortest_paths)
# for path in shortest_paths:
#     print(path, alg.compute_path_length(path))

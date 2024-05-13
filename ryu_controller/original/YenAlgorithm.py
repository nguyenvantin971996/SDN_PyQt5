from DijkstraAlgorithm import DijkstraAlgorithm
import copy
import sys
from decimal import Decimal

class Path(object):
    def __init__(self):
        self.vertices = []
        self.length = 0

class YenAlgorithm(object):

    def __init__(self, weight_map, vertices, src, dst, K):
        self._vertices = vertices
        self._weight_map = weight_map
        self._source_vertex = src
        self._destination_vertex = dst
        self.K = K

    def compute_shortest_paths(self):
        paths = []
        alg = DijkstraAlgorithm(self._weight_map, self._vertices)
        first_path = Path()
        first_path.vertices = alg.compute_shortest_path(self._source_vertex, self._destination_vertex)
        first_path.length = self.compute_path_length(first_path.vertices)
        paths.append(first_path)
        if len(first_path.vertices) == 0:
            return [], [], []
        B = []
        for k in range(1,self.K):
            for i in range(len(paths[k-1].vertices)-1):

                weight = copy.deepcopy(self._weight_map)

                spurNode = paths[k-1].vertices[i]
                rootPath = paths[k-1].vertices[:i+1]

                remove_edges = []
                for m in range(k):
                    if rootPath == paths[m].vertices[:i+1]:
                        item_1 = (paths[m].vertices[i], paths[m].vertices[i+1])
                        if item_1 not in remove_edges:
                            remove_edges.append(item_1)
                        item_2 = (paths[m].vertices[i+1], paths[m].vertices[i])
                        if item_2 not in remove_edges:
                            remove_edges.append(item_2)
                
                for m in range(i):
                    for node_2 in weight[rootPath[m]].keys():
                        item_1 = (rootPath[m], node_2)
                        if item_1 not in remove_edges:
                            remove_edges.append(item_1)
                        item_2 = (node_2, rootPath[m])
                        if item_2 not in remove_edges:
                            remove_edges.append(item_2)
                
                for item in remove_edges:
                    del weight[item[0]][item[1]]

                alg_d = DijkstraAlgorithm(weight, self._vertices)
                spurpath = alg_d.compute_shortest_path(spurNode, self._destination_vertex)
                if len(spurpath) != 0:
                    rootPath.pop()
                    rootPath.extend(spurpath)

                    path = Path()
                    path.vertices = copy.deepcopy(rootPath)
                    path.length = self.compute_path_length(path.vertices)
                    
                    dk = True
                    for path_b in B:
                        if path_b.vertices == path.vertices:
                            dk = False
                    if dk:
                        B.append(copy.deepcopy(path))
            
            if not B:
                break

            B.sort(key=lambda x: x.length)
            paths.append(copy.deepcopy(B[0]))
            B.pop(0)

        vertices_paths = [pth.vertices for pth in paths]
        edges_paths = self.compute_edges_of_paths(vertices_paths)
        length_paths = [float(pth.length) for pth in paths]
        return vertices_paths, edges_paths, length_paths

    def compute_edges_of_paths(self, vertices_paths):
        edges_of_paths = []
        for vertices in vertices_paths:
            edges = [(vertices[i], vertices[i + 1]) for i in range(len(vertices) - 1)]
            edges_of_paths.append(edges)
        return edges_of_paths
    
    def compute_path_length(self, vertices):
        path_length = 0
        for i in range(len(vertices) - 1):
            u = vertices[i]
            v = vertices[i + 1]
            path_length += self._weight_map[u][v]
        return path_length



# import numpy as np
# values = [0,0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9,1]
# # values = [0,1,2,3,4,5,6,7,8,9,10]
# vertices = [1,2,3,4,5,6,7,8]
# for i in range(1000):
#     weight_map={
#         1:{2:None,3:None},
#         2:{1:None,4:None,6:None},
#         3:{1:None,4:None,7:None},
#         4:{2:None,3:None,5:None},
#         5:{4:None,6:None,7:None},
#         6:{2:None,5:None,8:None},
#         7:{3:None,5:None,8:None},
#         8:{6:None,7:None}
#     }
#     for node_1 in weight_map.keys():
#         for node_2 in weight_map[node_1].keys():
#             if weight_map[node_2][node_1] != None:
#                 weight_map[node_1][node_2] = weight_map[node_2][node_1]
#             else:
#                 weight_map[node_1][node_2] = Decimal(str(np.random.choice(values)))
#     alg = YenAlgorithm(weight_map, vertices, 1, 8, 4)
#     paths_vertices, paths_edges, paths_length = alg.compute_shortest_paths()
#     print(paths_length)

# import networkx as nx
# from itertools import islice


# # Create a graph
# G = nx.Graph()

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


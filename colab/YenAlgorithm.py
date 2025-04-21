from DijkstraAlgorithm import DijkstraAlgorithm
import copy
class Path(object):
    def __init__(self):
        self.path_vertices = []
        self.dictance = 0

class YenAlgorithm(object):

    def __init__(self, weight_map, vertices, src, dst, K):
        self._vertices = vertices
        self._weight_map = weight_map
        self._source_vertex = src
        self._destination_vertex = dst
        self.K = K

    def compute_shortest_paths(self):
        paths =[]
        alg = DijkstraAlgorithm(self._weight_map,self._vertices)
        path_0 = alg.compute_shortest_path(self._source_vertex,self._destination_vertex)
        paths.append(path_0)
        B = []
        for i in range(1,self.K):
            for j in range(len(paths[i-1])-1):
                path = Path()
                weight = copy.deepcopy(self._weight_map)
                rootPath = paths[i-1][:j+1]
                spurNode = paths[i-1][j]
                for m in range(i):
                    if (rootPath == paths[m][:j+1]):
                        weight[paths[m][j]][paths[m][j+1]] = 9999999999
                        weight[paths[m][j+1]][paths[m][j]] = 9999999999
                for m in range(j):
                    for node_2 in weight[rootPath[m]].keys():
                        weight[rootPath[m]][node_2] = 9999999999
                        weight[node_2][rootPath[m]] = 9999999999
                alg_d = DijkstraAlgorithm(weight,self._vertices)
                spurpath = alg_d.compute_shortest_path(spurNode,self._destination_vertex)
                rootPath.pop()
                rootPath.extend(spurpath)
                path.path_vertices = copy.deepcopy(rootPath)
                for m in range(len(path.path_vertices)-1):
                    path.dictance += self._weight_map[path.path_vertices[m]][path.path_vertices[m+1]]
                dk = True
                for path_b in B:
                    if(path_b.path_vertices == path.path_vertices):
                        dk = False
                check = 0
                for m in range(len(spurpath)-1):
                    check += weight[spurpath[m]][spurpath[m+1]]
                if(check>=9999999999):
                    dk = False
                if(dk):
                    B.append(copy.deepcopy(path))
            B.sort(key=lambda x: x.dictance)
            paths.append(copy.deepcopy(B[0].path_vertices))
            B.pop(0)
        return paths
# weight_map={}
# temp = 0
# with open('metric_data.txt') as f:
#     for line in f:
#         strt = line
#         strt2 = strt.split(':')
#         my_result = list(map(int, strt2[0].split(',')))
#         if (temp!=my_result[0]):
#             weight_map[my_result[0]]={}
#         weight_map[my_result[0]][my_result[1]] = int(strt2[1])
#         temp = my_result[0]
# vertices = [1,2,3,4,5,6,7,8,9,10]
# alg = YenAlgorithm(weight_map,vertices,1,4,10)
# paths_vertices = alg.compute_shortest_paths()
# paths_length = []
# for path in paths_vertices:
#     s = 0
#     for i in range(len(path)-1):
#         s+= weight_map[path[i]][path[i+1]]
#     paths_length.append(s)
# print(paths_length)
from ABC import ABC
from BFA import BFA
from FA import FA
from AS import AS
from ACS import ACS
from GA import GA

class SI:
    def __init__(self, weight_map, src, dst, K, N, Max, algorithm_type):
        self.weight_map = weight_map
        self.src = src
        self.dst = dst
        self.K = K
        self.N = N
        self.Max = Max
        self.algorithm_type = algorithm_type
                
    def run(self):
        if self.algorithm_type == 'ABC':
            algorithm = ABC(self.weight_map, self.src, self.dst, self.K, self.N, self.Max, int(self.Max/5))
        elif self.algorithm_type == 'ACS':
            algorithm = ACS(self.weight_map, self.src, self.dst, self.K, self.N, self.Max, 0.1, 1, 2, 0.5, 1)
        elif self.algorithm_type == 'AS':
            algorithm = AS(self.weight_map, self.src, self.dst, self.K, self.N, self.Max, 0.1, 1, 2, 1)
        elif self.algorithm_type == 'BFA':
            algorithm = BFA(self.weight_map, self.src, self.dst, self.K, self.N, self.Max, 0.7, 2, 2)
        elif self.algorithm_type == 'FA':
            algorithm = FA(self.weight_map, self.src, self.dst, self.K, self.N, self.Max, 1, 1, 1)
        elif self.algorithm_type == 'GA':
            algorithm = GA(self.weight_map, self.src, self.dst, self.K, self.N, self.Max, 0.7, 0.7, 2)
        paths, paths_edges, pw = algorithm.compute_shortest_paths()
        return paths, paths_edges, pw
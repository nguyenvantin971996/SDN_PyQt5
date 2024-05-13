import numpy as np
import copy

class Ant(object):
    def __init__(self):
        self.path = np.array([], dtype=int)
        self.fitness = np.inf
        self.delta = 0

class ACS:

    def __init__(self, weight_map, src, dst, K, N, Max, p, a, b, p0, Q):
        self.weight_map = weight_map
        self.switches = np.array(list(weight_map.keys()))
        self.src = src
        self.dst = dst
        self.K = K

        self.fitness_max = self.get_fitness_max()

        self.N = N
        self.Max = Max
        self.p = p
        self.a = a
        self.b = b
        self.p0 = p0
        self.Q = Q

        self.colony = [Ant() for i in range(self.N)]
        self.candidates = []
        self.best = []
        self.Lnn = self.find_Lnn()
        self.t0 = 1/(len(self.switches)*self.Lnn)
        self.pheromone = self.create_pheromone()
    
    def get_fitness_max(self):
        s = 0
        for k1 in self.weight_map.keys():
            for k2 in self.weight_map[k1].keys():
                s += self.weight_map[k1][k2]
        return s
    
    def find_Lnn(self):
        path = [self.src]
        current_switch = self.src
        while current_switch != self.dst:
            neighbors = {k: v for k, v in self.weight_map[current_switch].items() if k not in path}
            if not neighbors:
                return self.fitness_max
            next_switch, _ = min(neighbors.items(), key=lambda x: x[1])
            current_switch = next_switch
            path.append(current_switch)
        return self.evaluate(path)
    
    def create_pheromone(self):
        pheromone = {}
        for sw_1 in self.weight_map:
            pheromone[sw_1] = {}
            for sw_2 in self.weight_map[sw_1]:
                pheromone[sw_1][sw_2] = self.t0
        return pheromone

    def create_path(self):
        for ant in self.colony:
            path = [self.src]
            current_switch = self.src
            while current_switch != self.dst:
                path_np = np.array(path)
                neighbor_switches_keys = np.array(list(self.weight_map[current_switch].keys()))
                neighbor_switches = np.setdiff1d(neighbor_switches_keys, path_np)

                if neighbor_switches.size == 0:
                    path = [self.src]
                    current_switch = self.src
                else:
                    current_switch = self.get_next_switch(neighbor_switches.tolist(), current_switch)
                    path.append(current_switch)

            ant.path = np.array(path, dtype=int)
            ant.fitness = self.evaluate(ant.path)
            ant.delta = self.Q / ant.fitness

    def get_next_switch(self, neighbor_switches, current_switch):
        probabilities = np.zeros(len(neighbor_switches))
        for i, sw in enumerate(neighbor_switches):
            x = self.pheromone[current_switch][sw]
            y = float(1 / self.weight_map[current_switch][sw])
            probabilities[i] = x ** self.a * y ** self.b
        probabilities /= probabilities.sum()
        sw_max = neighbor_switches[np.argmax(probabilities)]
        
        if np.random.rand() <= self.p0:
            next_switch = sw_max
        else:
            next_switch = np.random.choice(neighbor_switches, p=probabilities)
            self.local_pheromone_update(current_switch, next_switch)
        return next_switch

    def local_pheromone_update(self, current_switch, next_switch):
        self.pheromone[current_switch][next_switch] = (self.pheromone[current_switch][next_switch] * (1 - self.p) + self.p * self.t0)

    def evaluate(self, path):
        if len(path) == 0:
            return self.fitness_max
        else:
            total_weight = 0
            for i in range(len(path) - 1):
                current_switch = path[i]
                next_switch = path[i + 1]
                weight = self.weight_map[current_switch][next_switch]
                total_weight += weight
            return total_weight
    
    def global_pheromone_update(self):
            self.colony.sort(key=lambda ant: ant.fitness)
            best_ant = self.colony[0]
            for i in range(len(best_ant.path) - 1):
                p1 = best_ant.path[i]
                p2 = best_ant.path[i + 1]
                self.pheromone[p1][p2] = (1 - self.p) * self.pheromone[p1][p2] + self.p * best_ant.delta
     
    def memorize_candidates(self):
        self.colony.sort(key=lambda x: x.fitness)
        candidates = []
        for ant in self.colony:
            if len(candidates) >= self.K:
                break
            if not any(np.array_equal(ant.path, candidate.path) for candidate in candidates):
                candidates.append(copy.deepcopy(ant))
        self.candidates.extend(candidates) 
    
    def get_best(self):
        self.candidates.sort(key=lambda x: x.fitness)
        unique_best = []
        for candidate in self.candidates:
            if len(unique_best) >= self.K:
                break
            if not any(np.array_equal(candidate.path, ant.path) for ant in unique_best):
                unique_best.append(copy.deepcopy(candidate))
        self.best = unique_best

    def show(self):
        for item in self.colony:
            print(item.path, item.fitness)
        print('---------------------------------------------')

    def compute_edges_of_paths(self, vertices_paths):
        edges_of_paths = []
        for vertices in vertices_paths:
            edges = [(vertices[i], vertices[i + 1]) for i in range(len(vertices) - 1)]
            edges_of_paths.append(edges)
        return edges_of_paths
        
    def compute_shortest_paths(self):
        for iteration in range(self.Max):
            self.create_path()
            self.global_pheromone_update()
            self.memorize_candidates()
            # self.show()
        self.get_best()
        vertices_paths = [solution.path.tolist() for solution in self.best]
        edges_paths = self.compute_edges_of_paths(vertices_paths)
        length_paths = [float(solution.fitness) for solution in self.best]
        
        return vertices_paths, edges_paths, length_paths

# import time
# from get_metric import getMetric
# from YenAlgorithm import YenAlgorithm
# link_costs = getMetric('../topo_mininet/10_nodes.json')
# alg = ACS(link_costs, 1, 10, 4, 10, 100, 0.1, 0.1, 0.5, 0.9, 1)
# start = time.time()
# paths, paths_edges, pw = alg.compute_shortest_paths()
# end = time.time()
# print(end - start)
# print(paths, pw)
# alg_2 = YenAlgorithm(link_costs, 1, 10, 4)
# start = time.time()
# paths, paths_edges, pw = alg_2.compute_shortest_paths()
# end = time.time()
# print(end - start)
# print(paths, pw)
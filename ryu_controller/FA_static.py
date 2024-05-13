import numpy as np
import copy

class Solution(object):
    def __init__(self):
        self.path = np.array([], dtype=int)
        self.fitness = np.inf
        self.code = np.array([], dtype=float)

class FA:

    def __init__(self, weight_map, src, dst, K, N, Max, y, a0, b0, modify=False):
        self.weight_map = weight_map
        self.switches = np.array(list(weight_map.keys()))
        self.src = src
        self.dst = dst
        self.K = K

        self.fitness_max = self.get_fitness_max()

        self.N = N
        self.Max = Max
        self.y = y
        self.a0 = a0
        self.b0 = b0

        self.modify = modify
        
        self.population = [self.create_solution() for i in range(self.N)]
        self.candidates = []
        self.best = []

    def get_fitness_max(self):
        s = 0
        for k1 in self.weight_map.keys():
            for k2 in self.weight_map[k1].keys():
                s += self.weight_map[k1][k2]
        return s
    
    def create_solution(self):
        newSolution = Solution()
        code = np.random.uniform(-1, 1, self.switches.size)
        path = self.decode(code)
        newSolution.code = code
        newSolution.path = path
        newSolution.fitness = self.evaluate(path)
        return newSolution
    
    def decode(self, code):
        path = [self.src]
        current_switch = self.src
        while current_switch != self.dst:
            neighbor_switches = np.setdiff1d(list(self.weight_map[current_switch].keys()), path)
            if neighbor_switches.size == 0:
                return np.array([], dtype=int)
            switch_min = neighbor_switches[np.argmin(code[neighbor_switches - 1])]
            current_switch = switch_min
            path.append(current_switch)
        return np.array(path)

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
    
    def normalize(self, code):
        mn = np.min(code)
        mx = np.max(code)
        normalized_code = -1 + 2 * (code - mn) / (mx - mn)
        return normalized_code

    
    def attract(self):
        if self.modify:
            for i in range(self.N):
                for j in range(self.N):
                    new_code = self.population[i].code
                    if self.population[i].fitness > self.population[j].fitness:
                        r2 = np.sum((self.population[i].code - self.population[j].code) ** 2)
                        b = self.b0 * np.exp(-self.y * r2)
                        new_code += b * (self.population[j].code - self.population[i].code)
                    e = np.random.rand(self.switches.size) - 0.5
                    new_code += self.a0 * 2 * e
                    new_code = self.normalize(new_code)
                    new_solution = Solution()
                    new_solution.code = new_code
                    new_solution.path = self.decode(new_code)
                    new_solution.fitness = self.evaluate(new_solution.path)
                    self.population[i] = new_solution
        else:
            for i in range(self.N):
                for j in range(self.N):
                    new_code = self.population[i].code
                    if self.population[i].fitness > self.population[j].fitness:
                        r2 = np.sum((self.population[i].code - self.population[j].code) ** 2)
                        b = self.b0 * np.exp(-self.y * r2)
                        new_code += b * (self.population[j].code - self.population[i].code)
                        e = np.random.rand(self.switches.size) - 0.5
                        new_code += self.a0 * 2 * e
                        new_code = self.normalize(new_code)
                        new_solution = Solution()
                        new_solution.code = new_code
                        new_solution.path = self.decode(new_code)
                        new_solution.fitness = self.evaluate(new_solution.path)
                        self.population[i] = new_solution
                    
    def memorize_candidates(self):
        self.population.sort(key=lambda x: x.fitness)
        candidates = []
        for solution in self.population:
            if len(candidates) >= self.K:
                break
            if not any(np.array_equal(solution.path, candidate.path) for candidate in candidates):
                candidates.append(copy.deepcopy(solution))
        self.candidates.extend(candidates) 
    
    def get_best(self):
        self.candidates.sort(key=lambda x: x.fitness)
        unique_best = []
        for candidate in self.candidates:
            if len(unique_best) >= self.K:
                break
            if not any(np.array_equal(candidate.path, solution.path) for solution in unique_best):
                unique_best.append(copy.deepcopy(candidate))
        self.best = unique_best

    def show(self):
        for item in self.population:
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
            self.attract()
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
# alg = FA(link_costs, 1, 10, 4, 10, 100, 1, 1, 1)
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
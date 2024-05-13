import numpy as np
import copy
import time

class Solution(object):
    def __init__(self):
        self.path = np.array([], dtype=int)
        self.fitness = np.inf
        self.code = np.array([], dtype=float)

class FA:

    def __init__(self, port_monitor, paths_dict, key, K, N, Max, y, a0, b0):
        self.port_monitor = port_monitor
        self.paths_dict = paths_dict
        self.key = key
        self.src = key[0]
        self.dst = key[2]
        self.paths_yen = paths_dict[key][0]
        self.K = K
        self.N = N
        self.Max = Max
        self.y = y
        self.a0 = a0
        self.b0 = b0
        self.a = 0

    def reset_1(self, weight_map={}):
        self.weight_map = weight_map
        self.switches = np.array(list(weight_map.keys()))
        self.fitness_max = self.get_fitness_max(weight_map)

    def reset_2(self):
        self.population = [self.create_solution() for i in range(self.N)]
        self.best = []
        for path in self.paths_yen:
            newSolution = Solution()
            newSolution.path = np.array(path, dtype=int)
            newSolution.fitness = self.evaluate(path)
            self.best.append(newSolution)
        self.best.sort(key=lambda x: x.fitness)
        self.make_change_best()
    
    def get_fitness_max(self, weight_map):
        s = 0
        for k1 in weight_map.keys():
            for k2 in weight_map[k1].keys():
                s += weight_map[k1][k2]
        return s

    def re_evaluate(self):
        for member in self.population:
            member.fitness = self.evaluate(member.path)
        for member in self.best:
            member.fitness = self.evaluate(member.path)
    
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
        for i in range(self.N):
            for j in range(self.N):
                new_code = self.population[i].code
                if self.population[i].fitness > self.population[j].fitness:
                    r2 = np.sum((self.population[i].code - self.population[j].code) ** 2)
                    b = self.b0 * np.exp(-self.y * r2)
                    new_code += b * (self.population[j].code - self.population[i].code)
                    e = np.random.rand(self.switches.size) - 0.5
                    new_code += self.a * 2 * e
                    new_code = self.normalize(new_code)
                else:
                    e = np.random.rand(self.switches.size) - 0.5
                    new_code += self.a * 2 * e
                    new_code = self.normalize(new_code)
                new_solution = Solution()
                new_solution.code = new_code
                new_solution.path = self.decode(new_code)
                new_solution.fitness = self.evaluate(new_solution.path)
                self.population[i] = new_solution
                    
    def compare_best(self):
        self.population.sort(key=lambda x: x.fitness)
        candidates = []
        for solution in self.population:
            if len(candidates) >= self.K:
                break
            if not any(np.array_equal(solution.path, candidate.path) for candidate in candidates):
                candidates.append(copy.deepcopy(solution))
        change_best = False
        for candidate in candidates:
            for id in range(len(self.best)):
                if (not any(np.array_equal(solution.path, candidate.path) for solution in self.best)) and candidate.fitness < self.best[id].fitness:
                    self.best[id] = copy.deepcopy(candidate)
                    change_best = True
                    break
        if change_best == True:
            self.make_change_best()
    
    def make_change_best(self):
        self.paths_dict[self.key][0] = [solution.path.tolist() for solution in self.best]
        self.paths_dict[self.key][1] = self.compute_edges_of_paths(self.paths_dict[self.key][0])
        self.paths_dict[self.key][2] = [float(solution.fitness) for solution in self.best]

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
        weight_map_0 = self.port_monitor.get_inf()
        self.reset_1(weight_map_0)
        self.reset_2()
        for iteration in range(self.Max):

            if iteration % (self.Max//10) == 0:
                weight_map = self.port_monitor.get_inf()
                self.reset_1(weight_map)
                self.re_evaluate()

            self.a = self.a0*pow(0.99, iteration)
            self.attract()
            self.compare_best()
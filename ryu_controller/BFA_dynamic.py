import numpy as np
import copy
import time

class Solution(object):
    def __init__(self):
        self.path = np.array([], dtype=int)
        self.fitness = np.inf
        self.code = np.array([], dtype=float)
        self.velocity = np.array([], dtype=float)
        self.best_local_code = np.array([], dtype=float)
        self.best_local_fitness = np.inf

class BFA:

    def __init__(self, port_monitor, paths_dict, key, K, N, Max, w, c1, c2, patience):
        self.port_monitor = port_monitor
        self.paths_dict = paths_dict
        self.weight_map = self.port_monitor.get_link_costs()

        self.key = key
        self.src = key[0]
        self.dst = key[2]
        self.paths_yen = paths_dict[key][0]

        self.K = K
        self.N = N
        self.Max = Max
        self.w = w
        self.c1 = c1
        self.c2 = c2

        self.patience = patience
        self.no_improvement_count = 0

        self.best_global_solution = None
        self.population = None
        self.best = None

    def reset_1(self):
        self.switches = np.array(list(self.weight_map.keys()))
        self.fitness_max = self.get_fitness_max(self.weight_map)

    def reset_2(self):
        if self.best_global_solution is None or self.population is None or self.best is None:
            self.best_global_solution = Solution()
            self.population = [self.create_solution() for i in range(self.N)]
            self.best = []
            for path in self.paths_yen:
                new_solution = Solution()
                new_solution.path = np.array(path, dtype=int)
                new_solution.fitness = self.evaluate(path)
                self.best.append(new_solution)
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
        self.best.sort(key=lambda x: x.fitness)
        self.make_change_best()

    def create_solution(self):
        new_solution = Solution()
        code = np.random.uniform(-1, 1, self.switches.size)
        path = self.decode(code)
        new_solution.code = code
        new_solution.path = path
        new_solution.fitness = self.evaluate(path)

        new_solution.velocity = np.random.uniform(-0.5, 0.5, len(self.switches))
        new_solution.best_local_code = code.copy()
        new_solution.best_local_fitness = new_solution.fitness

        if new_solution.best_local_fitness <= self.best_global_solution.fitness:
            self.best_global_solution.code = new_solution.best_local_code.copy()
            self.best_global_solution.fitness = new_solution.best_local_fitness

        return new_solution
    
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
    
    def update_local_global(self, solution):
        if solution.fitness <= solution.best_local_fitness:
            solution.best_local_code = solution.code.copy()
            solution.best_local_fitness = solution.fitness
            if solution.best_local_fitness <= self.best_global_solution.fitness:
                self.best_global_solution.code = solution.best_local_code.copy()
                self.best_global_solution.fitness = solution.best_local_fitness

    def update_velocity_position(self):
        for i in range(self.N):
            velocity = self.population[i].velocity.copy()
            code = self.population[i].code.copy()

            path = np.array([], dtype=int)
            r1, r2 = np.random.rand(2, len(self.switches))
            v1 = self.c1 * r1 * (self.population[i].best_local_code - code)
            v2 = self.c2 * r2 * (self.best_global_solution.code - code)
            velocity = self.w * velocity + v1 + v2
            np.clip(velocity, -0.5, 0.5, out=velocity)

            code += velocity
            code = self.normalize(code)
            path = self.decode(code)

            self.population[i].velocity = velocity
            self.population[i].code = code
            self.population[i].path = path
            self.population[i].fitness = self.evaluate(path)
            self.update_local_global(self.population[i])

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
                if (not any(np.array_equal(candidate.path, solution.path) for solution in self.best)) and candidate.fitness < self.best[id].fitness:
                    self.best[id] = copy.deepcopy(candidate)
                    change_best = True
                    break
        if change_best:
            self.no_improvement_count = 0
            self.make_change_best()
        else:
            self.no_improvement_count += 1
    
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

    def compute_shortest_paths(self, time_limit):
        start = time.time()
        self.reset_1()
        self.reset_2()
        for iteration in range(self.Max):
            time.sleep(0)
            self.update_velocity_position()
            self.compare_best()
            self.reset_1()
            self.re_evaluate()
            end = time.time()
            if end - start > time_limit:
                break
            if self.no_improvement_count >= self.patience:
                break
            
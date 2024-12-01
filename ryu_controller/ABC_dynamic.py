import numpy as np
import copy
import time

class Solution(object):
    def __init__(self):
        self.path = np.array([], dtype=int)
        self.fitness = np.inf
        self.code = np.array([], dtype=float)
        self.counter = 0

class ABC:

    def __init__(self, port_monitor, paths_dict, key, K, N, Max, limit, patience):
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
        self.limit = limit

        self.patience = patience
        self.no_improvement_count = 0

        self.population = None
        self.best = None
    
    def reset_1(self):
        self.switches = np.array(list(self.weight_map.keys()))
        self.fitness_max = self.get_fitness_max(self.weight_map)

    def reset_2(self):
        if self.population is None or self.best is None:
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

    def initialization_phase(self):
        if self.population is None or self.best is None:
            self.population = [self.create_solution() for i in range(self.N)]
    
    def employed_phase(self):
        for i in range(self.N):
            choices = np.arange(self.N)
            choices = np.delete(choices, i)
            coceg = np.random.choice(choices)

            solution = self.population[i]
            new_code = np.copy(solution.code)
            d = np.random.randint(self.switches.size)
            fi = np.random.uniform(-1, 1)

            new_code[d] = solution.code[d] + fi * (solution.code[d] - self.population[coceg].code[d])
            new_code = self.normalize(new_code)
            new_path = self.decode(new_code)
            new_fitness = self.evaluate(new_path)
            if new_fitness < solution.fitness:
                solution.code = new_code
                solution.path = new_path
                solution.fitness = new_fitness
                solution.counter = 0
            else:
                solution.counter += 1

    def onlooker_phase(self):
        fitness_vector = np.array([1.0 / (1.0 + float(solution.fitness)) for solution in self.population])
        total_fitness = np.sum(fitness_vector)
        prob = fitness_vector / total_fitness    
        for i in range(self.N):
            index_solution = np.random.choice(np.arange(self.N), p=prob)
            choices = np.arange(self.N)
            choices = np.delete(choices, index_solution)
            coceg = np.random.choice(choices)
            
            solution = self.population[index_solution]
            new_code = np.copy(solution.code)
            d = np.random.randint(self.switches.size)
            fi = np.random.uniform(-1, 1)

            new_code[d] = solution.code[d] + fi * (solution.code[d] - self.population[coceg].code[d])
            new_code = self.normalize(new_code)
            new_path = self.decode(new_code)
            new_fitness = self.evaluate(new_path)
            if new_fitness < solution.fitness:
                solution.code = new_code
                solution.path = new_path
                solution.fitness = new_fitness
                solution.counter = 0
            else:
                solution.counter += 1

    def scout_phase(self):
        for i in range(self.N):
            if self.population[i].counter > self.limit:
                self.population[i] = self.create_solution()
    
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
        for item in self.best:
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
        self.initialization_phase()
        for iteration in range(self.Max):
            time.sleep(0)
            self.employed_phase()
            self.onlooker_phase()
            self.scout_phase()
            self.compare_best()
            self.reset_1()
            self.re_evaluate()
            end = time.time()
            if end - start > time_limit:
                break
            if self.no_improvement_count >= self.patience:
                break
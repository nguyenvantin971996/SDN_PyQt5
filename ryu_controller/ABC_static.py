import numpy as np
import copy

class Solution(object):
    def __init__(self):
        self.path = np.array([], dtype=int)
        self.fitness = np.inf
        self.code = np.array([], dtype=float)
        self.counter = 0

class ABC:

    def __init__(self, weight_map, src, dst, K, N, Max, limit):
        self.weight_map = weight_map
        self.switches = np.array(list(weight_map.keys()))
        self.src = src
        self.dst = dst
        self.K = K

        self.fitness_max = self.get_fitness_max()

        self.N = N
        self.Max = Max

        self.population = []
        self.candidates = []
        self.best = []

        self.limit = limit
    
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

    def initialization_phase(self):
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
        fitness_vector = np.array([1.0 / (1.0 + float(solution.fitness))  for solution in self.population])
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

        for candidate in candidates:
            if len(self.best) < self.K:
                self.best.append(copy.deepcopy(candidate))
                self.best.sort(key=lambda x: x.fitness)

            else:
                for id in range(len(self.best)):
                    if (not any(np.array_equal(candidate.path, solution.path) for solution in self.best)) and candidate.fitness < self.best[id].fitness:
                        self.best[id] = copy.deepcopy(candidate)
                        break

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
        self.initialization_phase()
        for iteration in range(self.Max):
            self.employed_phase()
            self.onlooker_phase()
            self.scout_phase()
            self.compare_best()

        vertices_paths = [solution.path.tolist() for solution in self.best]
        edges_paths = self.compute_edges_of_paths(vertices_paths)
        length_paths = [float(solution.fitness) for solution in self.best]
        
        return vertices_paths, edges_paths, length_paths
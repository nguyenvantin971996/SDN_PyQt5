import numpy as np
import copy

class Solution(object):
    def __init__(self):
        self.path = np.array([], dtype=int)
        self.fitness = np.inf

class GA:
    def __init__(self, weight_map, src, dst, K, N, Max, Pc, Pm, Ts):
        self.weight_map = weight_map
        self.src = src
        self.dst = dst
        self.K = K

        self.fitness_max = self.get_fitness_max()

        self.N = N
        self.Max = Max
        self.Pm = Pm
        self.Pc = Pc
        self.Ts = Ts

        self.population = [self.create_solution() for _ in range(self.N)]
        self.candidates = []
        self.best = []
    
    def get_fitness_max(self):
        s = 0
        for k1 in self.weight_map.keys():
            for k2 in self.weight_map[k1].keys():
                s += self.weight_map[k1][k2]
        return s

    def create_solution(self):
        new_solution = Solution()
        new_solution.path = np.append(new_solution.path, self.src)
        current_switch = self.src
        while current_switch != self.dst:
            neighbor_switches_keys = np.array(list(self.weight_map[current_switch].keys()))
            neighbor_switches = np.setdiff1d(neighbor_switches_keys, new_solution.path)
            if neighbor_switches.size == 0:
                new_solution.path = np.array([self.src], dtype=int)
                current_switch = self.src
            else:
                next_switch = np.random.choice(neighbor_switches)
                new_solution.path = np.append(new_solution.path, next_switch)
                current_switch = next_switch
        new_solution.fitness = self.evaluate(new_solution.path)
        return new_solution

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

    def correct_solution(self, solution):
        path = solution.path
        for i in range(1, len(path) - 2):
            duplicates = np.where(path[i] == path[i+1:])[0] + i + 1
            if duplicates.size > 0:
                solution.path = np.delete(path, np.arange(i+1, duplicates[0] + 1))
                break
        return solution

    def exchange_solution(self, parents_1, parents_2):
        path_1 = parents_1.path
        path_2 = parents_2.path
        for i in range(1, len(path_1) - 1):
            idx_1 = np.where(path_2 == path_1[i])[0]
            if idx_1.size > 0:
                j = idx_1[0]
                tail_1 = path_1[i+1:]
                tail_2 = path_2[j+1:]
                parents_1.path = np.hstack((path_1[:i+1], tail_2))
                parents_2.path = np.hstack((path_2[:j+1], tail_1))
                break
        return parents_1, parents_2

    def crossover(self):
        children = []
        for i in range(self.N // 2):
            father, mother = np.random.choice(self.N, 2, replace=False)
            parent_1 = copy.deepcopy(self.population[father])
            parent_2 = copy.deepcopy(self.population[mother])
            if np.random.rand() < self.Pc:
                child_1, child_2 = self.exchange_solution(parent_1, parent_2)
                child_1 = self.correct_solution(child_1)
                child_2 = self.correct_solution(child_2)
                child_1.fitness = self.evaluate(child_1.path)
                child_2.fitness = self.evaluate(child_2.path)
            else:
                child_1, child_2 = parent_1, parent_2

            children.extend([child_1, child_2])

        if len(children) < self.N:
            children.append(copy.deepcopy(children[-1]))

        self.population = children
    
    def mutation(self):
        for i in range(len(self.population)):
            if np.random.rand() < self.Pm:
                solution = self.population[i]
                mutation_point = np.random.randint(1, len(solution.path) - 1)

                new_path = solution.path[:mutation_point+1]
                current_switch = new_path[-1]

                while current_switch != self.dst:
                    neighbor_switches_keys = np.array(list(self.weight_map[current_switch].keys()))
                    neighbor_switches = np.setdiff1d(neighbor_switches_keys, new_path)
                    if neighbor_switches.size == 0:
                        new_path = solution.path[:mutation_point+1]
                        current_switch = new_path[-1]
                    else:
                        next_switch = np.random.choice(neighbor_switches)
                        new_path = np.append(new_path, next_switch)
                        current_switch = next_switch
                solution.path = np.array(new_path, dtype=int)
                solution.fitness = self.evaluate(solution.path)
                
    def selection(self):
        selected_population = []
        for _ in range(self.N):
            tournament_indices = np.random.randint(0, len(self.population), self.Ts)
            tournament = [self.population[i] for i in tournament_indices]
            winner = min(tournament, key=lambda x: x.fitness)
            selected_population.append(copy.deepcopy(winner))
        self.population = selected_population
    
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
            self.crossover()
            self.mutation()
            self.selection()
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
# alg = GA(link_costs, 1, 10, 4, 10, 100, 0.7, 0.7, 2)
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
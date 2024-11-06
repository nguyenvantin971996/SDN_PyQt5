import numpy as np
import copy

class Solution(object):
    def __init__(self):
        # Инициализация пути и начальной приспособленности
        self.path = np.array([], dtype=int)
        self.fitness = np.inf

class GA:
    def __init__(self, weight_map, src, dst, K, N, Max, Pc, Pm, Ts):
        # Инициализация параметров генетического алгоритма
        self.weight_map = weight_map  # Граф
        self.src = src  # Исходная вершина
        self.dst = dst  # Конечная вершина
        self.K = K  # Количество кратчайших путей

        self.fitness_max = self.get_fitness_max()  # Максимальная приспособленность

        self.N = N  # Размер популяции
        self.Max = Max  # Максимальное количество итераций
        self.Pc = Pc  # Вероятность скрещивания
        self.Pm = Pm  # Вероятность мутации
        self.Ts = Ts  # Размер турнира

        # Инициализация начальной популяции
        self.population = [self.create_solution() for _ in range(self.N)]
        self.candidates = []
        self.best = []
    
    def get_fitness_max(self):
        # Расчет максимальной приспособленности (сумма всех весов графа)
        s = 0
        for k1 in self.weight_map.keys():
            for k2 in self.weight_map[k1].keys():
                s += self.weight_map[k1][k2][1]
        return s/0.01

    def create_solution(self):
        # Создание случайного решения (пути)
        new_solution = Solution()
        new_solution.path = np.append(new_solution.path, self.src)  # Начать с исходной вершины
        current_switch = self.src
        while current_switch != self.dst:
            # Поиск соседних вершин, которых нет в пути
            neighbor_switches_keys = np.array(list(self.weight_map[current_switch].keys()))
            neighbor_switches = np.setdiff1d(neighbor_switches_keys, new_solution.path)
            if neighbor_switches.size == 0:
                # Если нет доступных соседей, начать заново
                new_solution.path = np.array([self.src], dtype=int)
                current_switch = self.src
            else:
                # Выбор случайного следующего узла
                next_switch = np.random.choice(neighbor_switches)
                new_solution.path = np.append(new_solution.path, next_switch)
                current_switch = next_switch
        new_solution.fitness = self.evaluate(new_solution.path)  # Оценка приспособленности
        return new_solution

    def evaluate(self, path):
        # Оценка приспособленности (длины пути)
        if len(path) == 0:
            return self.fitness_max
        else:
            total_weight = 0
            min_remain_bw = 100
            # Суммирование весов всех ребер в пути
            for i in range(len(path) - 1):
                current_switch = path[i]
                next_switch = path[i + 1]
                weight = self.weight_map[current_switch][next_switch][1]
                total_weight += weight

                if min_remain_bw > self.weight_map[current_switch][next_switch][0]:
                    min_remain_bw = self.weight_map[current_switch][next_switch][0]
                    
            if min_remain_bw == 0:
                return total_weight/0.01
            else:
                return total_weight*100/min_remain_bw

    def correct_solution(self, solution):
        # Коррекция решения (удаление циклов)
        path = solution.path
        for i in range(1, len(path) - 2):
            duplicates = np.where(path[i] == path[i+1:])[0] + i + 1
            if duplicates.size > 0:
                # Удаление повторяющихся узлов
                solution.path = np.delete(path, np.arange(i+1, duplicates[0] + 1))
                break
        return solution

    def exchange_solution(self, parents_1, parents_2):
        # Обмен частями пути между двумя родителями
        path_1 = parents_1.path
        path_2 = parents_2.path
        for i in range(1, len(path_1) - 1):
            idx_1 = np.where(path_2 == path_1[i])[0]
            if idx_1.size > 0:
                # Обмен "хвостами" путей
                j = idx_1[0]
                tail_1 = path_1[i+1:]
                tail_2 = path_2[j+1:]
                parents_1.path = np.hstack((path_1[:i+1], tail_2))
                parents_2.path = np.hstack((path_2[:j+1], tail_1))
                break
        return parents_1, parents_2

    def crossover(self):
        # Процедура скрещивания для создания новых решений
        children = []
        for i in range(self.N // 2):
            # Случайный выбор двух родителей
            father, mother = np.random.choice(self.N, 2, replace=False)
            parent_1 = copy.deepcopy(self.population[father])
            parent_2 = copy.deepcopy(self.population[mother])
            if np.random.rand() < self.Pc:
                # Если вероятность скрещивания выполнена, обмен частями пути
                child_1, child_2 = self.exchange_solution(parent_1, parent_2)
                child_1 = self.correct_solution(child_1)
                child_2 = self.correct_solution(child_2)
                child_1.fitness = self.evaluate(child_1.path)
                child_2.fitness = self.evaluate(child_2.path)
            else:
                # Если скрещивания нет, дети копируют родителей
                child_1, child_2 = parent_1, parent_2

            children.extend([child_1, child_2])

        if len(children) < self.N:
            # Добавление последнего решения, если необходимо
            children.append(copy.deepcopy(children[-1]))

        self.population = children
    
    def mutation(self):
        # Процедура мутации для изменения пути в решении
        for i in range(len(self.population)):
            if np.random.rand() < self.Pm:
                # Если вероятность мутации выполнена, изменение части пути
                solution = self.population[i]
                mutation_point = np.random.randint(1, len(solution.path) - 1)

                new_path = solution.path[:mutation_point+1]
                current_switch = new_path[-1]

                while current_switch != self.dst:
                    # Выбор нового пути после точки мутации
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
        # Процедура отбора решений для следующего поколения
        selected_population = []
        for _ in range(self.N):
            # Турнирный отбор
            tournament_indices = np.random.randint(0, len(self.population), self.Ts)
            tournament = [self.population[i] for i in tournament_indices]
            winner = min(tournament, key=lambda x: x.fitness)  # Выбирается решение с наименьшей приспособленностью
            selected_population.append(copy.deepcopy(winner))
        self.population = selected_population
    
    def compare_best(self):
        # Сравнение решений и выбор лучших для списка кандидатов
        self.population.sort(key=lambda x: x.fitness)
        candidates = []
        for solution in self.population:
            if len(candidates) >= self.K:
                break
            # Проверка на уникальность путей
            if not any(np.array_equal(solution.path, candidate.path) for candidate in candidates):
                candidates.append(copy.deepcopy(solution))

        for candidate in candidates:
            if len(self.best) < self.K:
                self.best.append(copy.deepcopy(candidate))
                self.best.sort(key=lambda x: x.fitness)

            else:
                # Замена наилучших решений в списке, если найдено лучшее
                for id in range(len(self.best)):
                    if (not any(np.array_equal(candidate.path, solution.path) for solution in self.best)) and candidate.fitness < self.best[id].fitness:
                        self.best[id] = copy.deepcopy(candidate)
                        break
                        
    def show(self):
        # Отображение текущей популяции
        for item in self.population:
            print(item.path, item.fitness)
        print('---------------------------------------------')

    def compute_edges_of_paths(self, vertices_paths):
        # Вычисление ребер по вершинам путей
        edges_of_paths = []
        for vertices in vertices_paths:
            edges = [(vertices[i], vertices[i + 1]) for i in range(len(vertices) - 1)]
            edges_of_paths.append(edges)
        return edges_of_paths
    
    def compute_shortest_paths(self):
        # Основной цикл генетического алгоритма
        for iteration in range(self.Max):
            self.crossover()
            self.mutation()
            self.selection()
            self.compare_best()

        # Возвращение кратчайших путей
        vertices_paths = [solution.path.tolist() for solution in self.best]
        edges_paths = self.compute_edges_of_paths(vertices_paths)
        length_paths = [float(solution.fitness) for solution in self.best]
        
        return vertices_paths, edges_paths, length_paths
import numpy as np
import copy

class Solution(object):
    def __init__(self):
        # Инициализация решения: путь, приспособленность, код, счетчик
        self.path = np.array([], dtype=int)
        self.fitness = np.inf
        self.code = np.array([], dtype=float)
        self.counter = 0

class ABC:
    def __init__(self, weight_map, src, dst, K, N, Max, limit):
        # Инициализация параметров алгоритма искусственной пчелиной колонии
        self.weight_map = weight_map  # Граф
        self.switches = np.array(list(weight_map.keys()))  # Вершины графа
        self.src = src  # Исходная вершина
        self.dst = dst  # Конечная вершина
        self.K = K  # Количество кратчайших путей

        self.fitness_max = self.get_fitness_max()  # Максимальная приспособленность

        self.N = N  # Размер популяции
        self.Max = Max  # Максимальное количество итераций

        self.population = []  # Популяция решений
        self.candidates = []
        self.best = []  # Лучшие решения

        self.limit = limit  # Порог для обновления решения

        # Инициализация списков для хранения значений
        self.best_fitness_per_iteration = []
        self.mean_fitness_per_iteration = []
    
    def get_fitness_max(self):
        # Вычисление максимальной приспособленности (сумма всех весов в графе)
        s = 0
        for k1 in self.weight_map.keys():
            for k2 in self.weight_map[k1].keys():
                s += self.weight_map[k1][k2]
        return s

    def create_solution(self):
        # Создание нового решения
        new_solution = Solution()
        code = np.random.uniform(-1, 1, self.switches.size)  # Генерация случайного кода
        path = self.decode(code)  # Декодирование пути из кода
        new_solution.code = code
        new_solution.path = path
        new_solution.fitness = self.evaluate(path)  # Оценка приспособленности
        return new_solution
    
    def decode(self, code):
        # Декодирование кода в путь
        path = [self.src]
        current_switch = self.src
        while current_switch != self.dst:
            # Поиск соседей, которые еще не посещены
            neighbor_switches = np.setdiff1d(list(self.weight_map[current_switch].keys()), path)
            if neighbor_switches.size == 0:
                return np.array([], dtype=int)  # Если не осталось доступных соседей, возвращаем пустой путь
            # Выбор вершины с минимальным кодом
            switch_min = neighbor_switches[np.argmin(code[neighbor_switches - 1])]
            current_switch = switch_min
            path.append(current_switch)
        return np.array(path)

    def evaluate(self, path):
        # Оценка приспособленности (длины пути)
        if len(path) == 0:
            return self.fitness_max
        else:
            total_weight = 0
            # Суммирование весов всех ребер в пути
            for i in range(len(path) - 1):
                current_switch = path[i]
                next_switch = path[i + 1]
                weight = self.weight_map[current_switch][next_switch]
                total_weight += weight
            return total_weight
    
    def normalize(self, code):
        # Нормализация кодов между -1 и 1
        mn = np.min(code)
        mx = np.max(code)
        normalized_code = -1 + 2 * (code - mn) / (mx - mn)
        return normalized_code

    def initialization_phase(self):
        # Фаза инициализации: создание начальной популяции
        self.population = [self.create_solution() for i in range(self.N)]
    
    def employed_phase(self):
        # Фаза рабочих пчел
        for i in range(self.N):
            # Выбор случайного решения
            choices = np.arange(self.N)
            choices = np.delete(choices, i)
            coceg = np.random.choice(choices)

            solution = self.population[i]
            new_code = np.copy(solution.code)
            d = np.random.randint(self.switches.size)  # Выбор случайного индекса
            fi = np.random.uniform(-1, 1)

            # Модификация кода
            new_code[d] = solution.code[d] + fi * (solution.code[d] - self.population[coceg].code[d])
            new_code = self.normalize(new_code)  # Нормализация нового кода
            new_path = self.decode(new_code)  # Декодирование нового пути
            new_fitness = self.evaluate(new_path)  # Оценка нового пути
            if new_fitness < solution.fitness:
                # Обновление решения, если новое лучше
                solution.code = new_code
                solution.path = new_path
                solution.fitness = new_fitness
                solution.counter = 0
            else:
                solution.counter += 1

    def onlooker_phase(self):
        # Фаза пчел-наблюдателей: выбор решения на основе вероятностей
        fitness_vector = np.array([1.0 / (1.0 + float(solution.fitness))  for solution in self.population])
        total_fitness = np.sum(fitness_vector)
        prob = fitness_vector / total_fitness  # Вероятность выбора решения
        
        for i in range(self.N):
            index_solution = np.random.choice(np.arange(self.N), p=prob)  # Выбор решения на основе вероятности
            choices = np.arange(self.N)
            choices = np.delete(choices, index_solution)
            coceg = np.random.choice(choices)
            
            solution = self.population[index_solution]
            new_code = np.copy(solution.code)
            d = np.random.randint(self.switches.size)  # Случайный индекс
            fi = np.random.uniform(-1, 1)

            # Модификация кода
            new_code[d] = solution.code[d] + fi * (solution.code[d] - self.population[coceg].code[d])
            new_code = self.normalize(new_code)  # Нормализация кода
            new_path = self.decode(new_code)  # Декодирование пути
            new_fitness = self.evaluate(new_path)
            if new_fitness < solution.fitness:
                # Обновление, если решение лучше
                solution.code = new_code
                solution.path = new_path
                solution.fitness = new_fitness
                solution.counter = 0
            else:
                solution.counter += 1

    def scout_phase(self):
        # Фаза пчел-разведчиков: замена решений, которые не улучшаются
        for i in range(self.N):
            if self.population[i].counter > self.limit:
                self.population[i] = self.create_solution()  # Замена решения

    def compare_best(self):
        # Сравнение решений и выбор лучших
        self.population.sort(key=lambda x: x.fitness)
        candidates = []
        for solution in self.population:
            if len(candidates) >= self.K:
                break
            if not any(np.array_equal(solution.path, candidate.path) for candidate in candidates):
                candidates.append(copy.deepcopy(solution))

        # total_k_fitness = sum(sol.fitness for sol in candidates) + (self.K - len(candidates)) * self.fitness_max
        # self.best_fitness_per_iteration.append(total_k_fitness)
        
        for candidate in candidates:
            if len(self.best) < self.K:
                self.best.append(copy.deepcopy(candidate))  # Добавление лучшего решения
                self.best.sort(key=lambda x: x.fitness)

            else:
                for id in range(len(self.best)):
                    if (not any(np.array_equal(candidate.path, solution.path) for solution in self.best)) and candidate.fitness < self.best[id].fitness:
                        self.best[id] = copy.deepcopy(candidate)
                        break

    def show(self):
        # Отображение текущих решений в популяции
        for item in self.population:
            print(item.path, item.fitness)
        print('---------------------------------------------')

    def compute_edges_of_paths(self, vertices_paths):
        # Вычисление ребер для каждого пути
        edges_of_paths = []
        for vertices in vertices_paths:
            edges = [(vertices[i], vertices[i + 1]) for i in range(len(vertices) - 1)]
            edges_of_paths.append(edges)
        return edges_of_paths

    def compute_shortest_paths(self):
        # Основной цикл выполнения алгоритма искусственной пчелиной колонии
        self.initialization_phase()
        for iteration in range(self.Max):
            self.employed_phase()
            self.onlooker_phase()
            self.scout_phase()
            self.compare_best()
        
            # Обновление значений для отображения графиков
            total_k_fitness = sum(sol.fitness for sol in self.best) + (self.K - len(self.best)) * self.fitness_max
            self.best_fitness_per_iteration.append(total_k_fitness)
            mean_fitness = np.mean([solution.fitness for solution in self.population])
            self.mean_fitness_per_iteration.append(mean_fitness)

        # Возвращение кратчайших путей, ребер и их длины
        vertices_paths = [solution.path.tolist() for solution in self.best]
        edges_paths = self.compute_edges_of_paths(vertices_paths)
        length_paths = [float(solution.fitness) for solution in self.best]
        
        return vertices_paths, edges_paths, length_paths, self.best_fitness_per_iteration, self.mean_fitness_per_iteration
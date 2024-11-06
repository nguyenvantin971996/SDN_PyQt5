import numpy as np
import copy

class Solution(object):
    def __init__(self):
        # Инициализация решения: путь, приспособленность, код, скорость, лучшие локальные решения
        self.path = np.array([], dtype=int)
        self.fitness = np.inf
        self.code = np.array([], dtype=float)
        self.velocity = np.array([], dtype=float)
        self.best_local_code = np.array([], dtype=float)
        self.best_local_fitness = np.inf


class BFA:
    def __init__(self, weight_map, src, dst, K, N, Max, w, c1, c2):
        # Инициализация параметров алгоритма стаи птиц
        self.weight_map = weight_map  # Граф
        self.switches = np.array(list(weight_map.keys()))  # Вершины графа
        self.src = src  # Исходная вершина
        self.dst = dst  # Конечная вершина
        self.K = K  # Количество кратчайших путей

        self.fitness_max = self.get_fitness_max()  # Максимальная приспособленность

        self.N = N  # Размер популяции
        self.Max = Max  # Максимальное количество итераций
        self.w = w  # Коэффициент инерции
        self.c1 = c1  # Когнитивный коэффициент
        self.c2 = c2  # Социальный коэффициент 

        # Глобальное лучшее решение
        self.best_global_solution = Solution()
        # Инициализация популяции решений
        self.population = [self.create_solution() for i in range(self.N)]
        self.candidates = []
        self.best = []  # Лучшие решения

        # Инициализация списков для хранения значений
        self.best_fitness_per_iteration = []
        self.mean_fitness_per_iteration = []

    def get_fitness_max(self):
        # Вычисление максимальной приспособленности (сумма всех весов графа)
        s = 0
        for k1 in self.weight_map.keys():
            for k2 in self.weight_map[k1].keys():
                s += self.weight_map[k1][k2][1]
        return s*100

    def create_solution(self):
        # Создание нового решения
        newSolution = Solution()
        code = np.random.uniform(-1, 1, self.switches.size)  # Генерация случайного кода
        path = self.decode(code)  # Декодирование пути из кода
        newSolution.code = code
        newSolution.path = path
        newSolution.fitness = self.evaluate(path)  # Оценка приспособленности

        # Инициализация скорости и локальных лучших решений
        newSolution.velocity = np.random.uniform(-0.5, 0.5, len(self.switches))
        newSolution.best_local_code = code.copy()
        newSolution.best_local_fitness = newSolution.fitness

        # Обновление глобального лучшего решения
        if newSolution.best_local_fitness <= self.best_global_solution.fitness:
            self.best_global_solution.code = newSolution.best_local_code.copy()
            self.best_global_solution.fitness = newSolution.best_local_fitness

        return newSolution
    
    def decode(self, code):
        # Декодирование кода в путь
        path = [self.src]
        current_switch = self.src
        while current_switch != self.dst:
            # Поиск соседних вершин, которые еще не посещены
            neighbor_switches = np.setdiff1d(list(self.weight_map[current_switch].keys()), path)
            if neighbor_switches.size == 0:
                return np.array([], dtype=int)  # Возврат пустого пути, если нет доступных соседей
            # Выбор вершины с минимальным значением в коде
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
                return total_weight*100
            else:
                return total_weight*100/min_remain_bw
    
    def normalize(self, code):
        # Нормализация кодов между -1 и 1
        mn = np.min(code)
        mx = np.max(code)
        normalized_code = -1 + 2 * (code - mn) / (mx - mn)
        return normalized_code
    
    def update_local_global(self, solution):
        # Обновление локальных и глобальных лучших решений
        if solution.fitness <= solution.best_local_fitness:
            solution.best_local_code = solution.code.copy()
            solution.best_local_fitness = solution.fitness
            if solution.best_local_fitness <= self.best_global_solution.fitness:
                self.best_global_solution.code = solution.best_local_code.copy()
                self.best_global_solution.fitness = solution.best_local_fitness

    def update_velocity_position(self):
        # Обновление скорости и позиции для каждой птицы
        for i in range(self.N):
            velocity = self.population[i].velocity.copy()
            code = self.population[i].code.copy()

            # Обновление скорости
            r1, r2 = np.random.rand(2, len(self.switches))
            v1 = self.c1 * r1 * (self.population[i].best_local_code - code)
            v2 = self.c2 * r2 * (self.best_global_solution.code - code)
            velocity = self.w * velocity + v1 + v2
            np.clip(velocity, -0.5, 0.5, out=velocity)  # Ограничение скорости

            # Обновление позиции
            code += velocity
            code = self.normalize(code)  # Нормализация кода
            path = self.decode(code)  # Декодирование пути из нового кода

            # Сохранение изменений
            self.population[i].velocity = velocity
            self.population[i].code = code
            self.population[i].path = path
            self.population[i].fitness = self.evaluate(path)
            self.update_local_global(self.population[i])

    def compare_best(self):
        # Сравнение решений и выбор лучших путей
        self.population.sort(key=lambda x: x.fitness)  # Сортировка по приспособленности
        candidates = []
        for solution in self.population:
            if len(candidates) >= self.K:
                break
            # Проверка на уникальность путей
            if not any(np.array_equal(solution.path, candidate.path) for candidate in candidates):
                candidates.append(copy.deepcopy(solution))

        # total_k_fitness = sum(sol.fitness for sol in candidates) + (self.K - len(candidates)) * self.fitness_max
        # self.best_fitness_per_iteration.append(total_k_fitness)
        
        for candidate in candidates:
            if len(self.best) < self.K:
                self.best.append(copy.deepcopy(candidate))  # Добавление лучших путей
                self.best.sort(key=lambda x: x.fitness)
            else:
                # Замена решений, если найдено лучшее
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
        # Основной цикл выполнения алгоритма стаи птиц
        for iteration in range(self.Max):
            self.update_velocity_position()  # Обновление скорости и позиций птиц
            self.compare_best()  # Сравнение лучших решений

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

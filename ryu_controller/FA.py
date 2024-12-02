import numpy as np
import copy

class Solution(object):
    def __init__(self):
        # Инициализация решения: путь, приспособленность, код
        self.path = np.array([], dtype=int)
        self.fitness = np.inf
        self.code = np.array([], dtype=float)

class FA:

    def __init__(self, weight_map, src, dst, K, N, Max, y, a0, b0, modify=False):
        # Инициализация параметров алгоритма светлячков
        self.weight_map = weight_map  # Граф
        self.switches = np.array(list(weight_map.keys()))  # Вершины графа
        self.src = src  # Исходная вершина
        self.dst = dst  # Конечная вершина
        self.K = K  # Количество кратчайших путей

        self.fitness_max = self.get_fitness_max()  # Максимальная приспособленность

        self.N = N  # Размер популяции
        self.Max = Max  # Максимальное количество итераций
        self.y = y  # Коэффициент поглощения света
        self.a0 = a0  # Параметр, контролирующий случайные шаги
        self.b0 = b0  # Базовый коэффициент яркости светлячков
        self.a = 0  # Текущий параметр, контролирующий случайные шаги

        self.modify = modify  # Флаг модификации поведения светлячков
        
        # Инициализация популяции светлячков
        self.population = [self.create_solution() for i in range(self.N)]
        self.candidates = []
        self.best = []  # Лучшие решения

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
        newSolution = Solution()
        code = np.random.uniform(-1, 1, self.switches.size)  # Генерация случайного кода
        path = self.decode(code)  # Декодирование пути из кода
        newSolution.code = code
        newSolution.path = path
        newSolution.fitness = self.evaluate(path)  # Оценка приспособленности
        return newSolution
    
    def decode(self, code):
        # Декодирование кода в путь
        path = [self.src]
        current_switch = self.src
        while current_switch != self.dst:
            # Поиск соседей, которые еще не посещены
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

    def attract(self):
        # Основной цикл притяжения светлячков друг к другу
        if self.modify:
            # Модифицированная версия притяжения
            for i in range(self.N):
                for j in range(self.N):
                    new_code = self.population[i].code
                    if self.population[i].fitness > self.population[j].fitness:
                        # Вычисление притяжения на основе расстояния и интенсивности света
                        r2 = np.sum((self.population[i].code - self.population[j].code) ** 2)
                        b = self.b0 * np.exp(-self.y * r2)
                        new_code += b * (self.population[j].code - self.population[i].code)
                    # Добавление случайного шума
                    e = np.random.rand(self.switches.size) - 0.5
                    new_code += self.a * 2 * e
                    new_code = self.normalize(new_code)
                    new_solution = Solution()
                    new_solution.code = new_code
                    new_solution.path = self.decode(new_code)
                    new_solution.fitness = self.evaluate(new_solution.path)
                    self.population[i] = new_solution
        else:
            # Оригинальная версия притяжения
            for i in range(self.N):
                for j in range(self.N):
                    new_code = self.population[i].code
                    if self.population[i].fitness > self.population[j].fitness:
                        r2 = np.sum((self.population[i].code - self.population[j].code) ** 2)
                        b = self.b0 * np.exp(-self.y * r2)
                        new_code += b * (self.population[j].code - self.population[i].code)
                        # Добавление случайного шума
                        e = np.random.rand(self.switches.size) - 0.5
                        new_code += self.a * 2 * e
                        new_code = self.normalize(new_code)
                        new_solution = Solution()
                        new_solution.code = new_code
                        new_solution.path = self.decode(new_code)
                        new_solution.fitness = self.evaluate(new_solution.path)
                        self.population[i] = new_solution
                    
    def compare_best(self):
        # Сравнение решений и выбор лучших путей
        self.population.sort(key=lambda x: x.fitness)  # Сортировка популяции по приспособленности
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
                self.best.append(copy.deepcopy(candidate))  # Добавление лучших путей в список
                self.best.sort(key=lambda x: x.fitness)
            else:
                # Замена решения, если найдено лучшее
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
        # Основной цикл выполнения алгоритма светлячков
        for iteration in range(self.Max):
            # Постепенное уменьшение a0
            self.a = self.a0 * pow(1, iteration)
            self.attract()  # Притяжение светлячков друг к другу
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
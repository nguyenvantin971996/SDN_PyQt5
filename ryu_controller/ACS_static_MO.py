import numpy as np
import copy

class Ant(object):
    def __init__(self):
        # Инициализация муравья: путь, приспособленность и изменение феромона
        self.path = np.array([], dtype=int)
        self.fitness = np.inf
        self.delta = 0

class ACS:
    def __init__(self, weight_map, src, dst, K, N, Max, p, a, b, q0, Q):
        # Инициализация параметров алгоритма системы муравьиной колонии
        self.weight_map = weight_map  # Граф
        self.switches = np.array(list(weight_map.keys()))  # Вершины графа
        self.src = src  # Исходная вершина
        self.dst = dst  # Конечная вершина
        self.K = K  # Количество кратчайших путей

        self.fitness_max = self.get_fitness_max()  # Максимальная приспособленность

        self.N = N  # Количество муравьев в колонии
        self.Max = Max  # Максимальное количество итераций
        self.p = p  # Коэффициент испарения феромона
        self.a = a  # Влияние феромона на выбор пути
        self.b = b  # Влияние длины пути на выбор
        self.q0 = q0  # Коэффициент жадности
        self.Q = Q  # Интенсивность феромона

        self.colony = [Ant() for i in range(self.N)]  # Инициализация колонии муравьев
        self.candidates = []
        self.best = []  # Лучшие решения
        self.Lnn = self.find_Lnn()  # Эвристическое значение Lnn (длина кратчайшего пути)
        self.t0 = 1/(len(self.switches) * self.Lnn)  # Начальная концентрация феромона
        self.pheromone = self.create_pheromone()  # Матрица феромонов

        # Инициализация списков для хранения значений
        self.best_fitness_per_iteration = []
        self.mean_fitness_per_iteration = []
    
    def get_fitness_max(self):
        # Расчет максимальной приспособленности (сумма всех весов графа)
        s = 0
        for k1 in self.weight_map.keys():
            for k2 in self.weight_map[k1].keys():
                s += self.weight_map[k1][k2][1]
        return s*100
    
    def find_Lnn(self):
        # Нахождение эвристической длины кратчайшего пути с жадным алгоритмом
        path = [self.src]
        current_switch = self.src
        while current_switch != self.dst:
            # Поиск ближайшего соседа, которого еще нет в пути
            neighbors = {k: v for k, v in self.weight_map[current_switch].items() if k not in path}
            if not neighbors:
                return self.fitness_max  # Если нет соседей, возвращаем максимальную приспособленность
            next_switch, _ = min(neighbors.items(), key=lambda x: x[1][1])  # Выбор наименьшего по весу соседа
            current_switch = next_switch
            path.append(current_switch)
        return self.evaluate(path)  # Оценка длины пути
    
    def create_pheromone(self):
        # Создание матрицы феромонов, инициализация значением t0
        pheromone = {}
        for sw_1 in self.weight_map:
            pheromone[sw_1] = {}
            for sw_2 in self.weight_map[sw_1]:
                pheromone[sw_1][sw_2] = self.t0
        return pheromone

    def create_path(self):
        # Создание пути для каждого муравья в колонии
        for ant in self.colony:
            path = [self.src]  # Начальный путь
            current_switch = self.src
            while current_switch != self.dst:
                path_np = np.array(path)
                # Поиск соседних вершин, которые еще не посещены
                neighbor_switches_keys = np.array(list(self.weight_map[current_switch].keys()))
                neighbor_switches = np.setdiff1d(neighbor_switches_keys, path_np)

                if neighbor_switches.size == 0:
                    # Если соседей нет, начать заново
                    path = [self.src]
                    current_switch = self.src
                else:
                    # Выбор следующего узла с использованием вероятностного метода
                    current_switch = self.get_next_switch(neighbor_switches.tolist(), current_switch)
                    path.append(current_switch)

            ant.path = np.array(path, dtype=int)  # Установка пути для муравья
            ant.fitness = self.evaluate(ant.path)  # Оценка приспособленности (длины пути)
            ant.delta = self.Q / ant.fitness  # Обновление значения delta феромона для муравья

    def get_next_switch(self, neighbor_switches, current_switch):
        # Выбор следующего узла с учетом феромона и длины ребра
        probabilities = np.zeros(len(neighbor_switches))
        for i, sw in enumerate(neighbor_switches):
            x = self.pheromone[current_switch][sw]  # Уровень феромона
            y = float(1 / self.weight_map[current_switch][sw][1])  # Обратное значение веса
            probabilities[i] = x ** self.a * y ** self.b  # Вычисление вероятности на основе феромона и веса
        probabilities /= probabilities.sum()  # Нормализация вероятностей
        sw_max = neighbor_switches[np.argmax(probabilities)]  # Выбор узла с максимальной вероятностью
        
        if np.random.rand() <= self.q0:
            next_switch = sw_max  # Жадный выбор на основе вероятности q0
        else:
            # Случайный выбор узла на основе вероятностей
            next_switch = np.random.choice(neighbor_switches, p=probabilities)
            self.local_pheromone_update(current_switch, next_switch)  # Локальное обновление феромона
        return next_switch

    def local_pheromone_update(self, current_switch, next_switch):
        # Локальное обновление уровня феромона
        self.pheromone[current_switch][next_switch] = self.pheromone[current_switch][next_switch] * (1 - self.p) + self.p * self.t0

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
    
    def global_pheromone_update(self):
        # Глобальное обновление уровня феромона по наилучшему решению
        self.colony.sort(key=lambda ant: ant.fitness)  # Сортировка муравьев по приспособленности
        best_ant = self.colony[0]  # Наилучший муравей
        for i in range(len(best_ant.path) - 1):
            p1 = best_ant.path[i]
            p2 = best_ant.path[i + 1]
            # Глобальное обновление феромона
            self.pheromone[p1][p2] = (1 - self.p) * self.pheromone[p1][p2] + self.p * best_ant.delta
     
    def compare_best(self):
        # Сравнение решений и выбор лучших путей
        self.colony.sort(key=lambda x: x.fitness)  # Сортировка муравьев по приспособленности
        candidates = []
        for solution in self.colony:
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
                # Замена наилучших решений, если найдено лучшее
                for id in range(len(self.best)):
                    if (not any(np.array_equal(candidate.path, solution.path) for solution in self.best)) and candidate.fitness < self.best[id].fitness:
                        self.best[id] = copy.deepcopy(candidate)
                        break

    def show(self):
        # Отображение текущих решений в колонии
        for item in self.colony:
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
        # Основной цикл выполнения алгоритма системы муравьиной колонии
        for iteration in range(self.Max):
            self.create_path()  # Создание путей для всех муравьев
            self.global_pheromone_update()  # Глобальное обновление феромонов
            self.compare_best()  # Сравнение и выбор лучших путей

            # Обновление значений для отображения графиков
            total_k_fitness = sum(sol.fitness for sol in self.best) + (self.K - len(self.best)) * self.fitness_max
            self.best_fitness_per_iteration.append(total_k_fitness)
            mean_fitness = np.mean([solution.fitness for solution in self.colony])
            self.mean_fitness_per_iteration.append(mean_fitness)

        # Возвращение кратчайших путей, ребер и их длины
        vertices_paths = [solution.path.tolist() for solution in self.best]
        edges_paths = self.compute_edges_of_paths(vertices_paths)
        length_paths = [float(solution.fitness) for solution in self.best]
        
        return vertices_paths, edges_paths, length_paths, self.best_fitness_per_iteration, self.mean_fitness_per_iteration
import numpy as np
import copy

class Ant(object):
    def __init__(self):
        # Инициализация муравья: путь, приспособленность и изменение феромона
        self.path = np.array([], dtype=int)
        self.fitness = np.inf
        self.delta = 0

class AS:
    def __init__(self, weight_map, src, dst, K, N, Max, p, a, b, Q):
        # Инициализация параметров алгоритма муравьиной системы
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
        self.Q = Q  # Константа для обновления феромона

        self.colony = [Ant() for i in range(self.N)]  # Инициализация колонии муравьев
        self.candidates = []
        self.best = []  # Лучшие пути
        self.Lnn = self.find_Lnn()  # Эвристическое значение Lnn (длина кратчайшего пути)
        self.t0 = 1 / (len(self.switches) * self.Lnn)  # Начальная концентрация феромона
        self.pheromone = self.create_pheromone()  # Матрица феромонов
    
    def get_fitness_max(self):
        # Расчет максимальной приспособленности (сумма всех весов графа)
        s = 0
        for k1 in self.weight_map.keys():
            for k2 in self.weight_map[k1].keys():
                s += self.weight_map[k1][k2][1]
        return s/0.01
    
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
        next_switch = np.random.choice(neighbor_switches, p=probabilities)  # Случайный выбор узла на основе вероятностей
        return next_switch

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
    
    def update_pheromone(self):
        # Обновление уровня феромонов на каждом ребре
        for sw_1, neighbors in self.pheromone.items():
            for sw_2 in neighbors:
                self.pheromone[sw_1][sw_2] *= (1 - self.p)  # Испарение феромона
        for ant in self.colony:
            for j in range(len(ant.path) - 1):
                p1, p2 = ant.path[j], ant.path[j + 1]
                # Добавление нового феромона, оставленного муравьем
                self.pheromone[p1][p2] += ant.delta
     
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
        # Основной цикл выполнения алгоритма муравьиной системы
        for iteration in range(self.Max):
            self.create_path()  # Создание путей для всех муравьев
            self.update_pheromone()  # Обновление уровня феромонов
            self.compare_best()  # Сравнение и выбор лучших путей

        # Возвращение кратчайших путей, ребер и их длины
        vertices_paths = [solution.path.tolist() for solution in self.best]
        edges_paths = self.compute_edges_of_paths(vertices_paths)
        length_paths = [float(solution.fitness) for solution in self.best]
        
        return vertices_paths, edges_paths, length_paths
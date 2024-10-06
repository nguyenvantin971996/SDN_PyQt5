import numpy as np
import copy
import time

class Solution(object):
    # Класс для представления решения в виде пути и его приспособленности
    def __init__(self):
        # Инициализация пустого пути и бесконечной приспособленности
        self.path = np.array([], dtype=int)
        self.fitness = np.inf

class GA:
    # Класс генетического алгоритма для нахождения кратчайшего пути
    def __init__(self, port_monitor, paths_dict, key, K, N, Max, Pc, Pm, Ts):
        # Инициализация генетического алгоритма с заданными параметрами
        self.port_monitor = port_monitor  # Монитор портов для получения данных о графе
        self.paths_dict = paths_dict  # Словарь путей
        self.weight_map = self.port_monitor.get_link_costs()  # Получение весов ребер

        self.key = key  # Ключ для текущего пути (источник, назначение)
        self.src = key[0]  # Исходная вершина
        self.dst = key[2]  # Конечная вершина
        self.paths_yen = paths_dict[key][0]  # Инициализация путей на основе алгоритма Йена

        self.K = K  # Количество кратчайших путей
        self.N = N  # Размер популяции
        self.Max = Max  # Максимальное количество итераций
        self.Pm = Pm  # Вероятность мутации
        self.Pc = Pc  # Вероятность скрещивания
        self.Ts = Ts  # Размер турнира для отбора
    
    def reset_1(self):
        # Сброс состояния алгоритма (вычисление максимальной приспособленности)
        self.switches = np.array(list(self.weight_map.keys()))
        self.fitness_max = self.get_fitness_max(self.weight_map)

    def reset_2(self):
        # Сброс начальной популяции и лучших решений
        self.population = [self.create_solution() for _ in range(self.N)]  # Создание популяции
        self.best = []  # Инициализация лучших решений
        for path in self.paths_yen:
            newSolution = Solution()  # Создание нового решения для каждого пути из Йена
            newSolution.path = np.array(path, dtype=int)  # Преобразование пути в массив
            newSolution.fitness = self.evaluate(path)  # Оценка приспособленности
            self.best.append(newSolution)  # Добавление решения в список лучших
        self.best.sort(key=lambda x: x.fitness)  # Сортировка лучших решений по приспособленности
        self.make_change_best()  # Обновление лучших решений в словаре путей
    
    def get_fitness_max(self, weight_map):
        # Вычисление максимальной приспособленности (суммы всех весов графа)
        s = 0
        for k1 in weight_map.keys():
            for k2 in weight_map[k1].keys():
                s += weight_map[k1][k2]
        return s
    
    def re_evaluate(self):
        # Повторная оценка популяции и лучших решений
        for member in self.population:
            member.fitness = self.evaluate(member.path)  # Оценка каждого решения в популяции
        for member in self.best:
            member.fitness = self.evaluate(member.path)  # Оценка лучших решений
        self.best.sort(key=lambda x: x.fitness)  # Сортировка лучших решений по приспособленности
        self.make_change_best()  # Обновление лучших решений
    
    def create_solution(self):
        # Создание случайного решения (случайный путь от источника до назначения)
        new_solution = Solution()
        new_solution.path = np.append(new_solution.path, self.src)  # Добавление источника в путь
        current_switch = self.src
        while current_switch != self.dst:
            # Поиск соседей и добавление случайного соседнего узла в путь
            neighbor_switches_keys = np.array(list(self.weight_map[current_switch].keys()))
            neighbor_switches = np.setdiff1d(neighbor_switches_keys, new_solution.path)
            if neighbor_switches.size == 0:
                # Если нет доступных соседей, начать заново
                new_solution.path = np.array([self.src], dtype=int)
                current_switch = self.src
            else:
                next_switch = np.random.choice(neighbor_switches)  # Случайный выбор следующего узла
                new_solution.path = np.append(new_solution.path, next_switch)
                current_switch = next_switch
        new_solution.fitness = self.evaluate(new_solution.path)  # Оценка пути
        return new_solution

    def evaluate(self, path):
        # Оценка приспособленности пути (сумма весов ребер)
        if len(path) == 0:
            return self.fitness_max  # Если путь пуст, вернуть максимальную приспособленность
        else:
            total_weight = 0
            for i in range(len(path) - 1):
                current_switch = path[i]
                next_switch = path[i + 1]
                weight = self.weight_map[current_switch][next_switch]  # Получение веса ребра
                total_weight += weight
            return total_weight

    def correct_solution(self, solution):
        # Коррекция пути (удаление циклов в решении)
        path = solution.path
        for i in range(1, len(path) - 2):
            duplicates = np.where(path[i] == path[i+1:])[0] + i + 1  # Поиск дубликатов в пути
            if duplicates.size > 0:
                solution.path = np.delete(path, np.arange(i+1, duplicates[0] + 1))  # Удаление циклов
                break
        return solution

    def exchange_solution(self, parents_1, parents_2):
        # Обмен частями пути между двумя родителями для скрещивания
        path_1 = parents_1.path
        path_2 = parents_2.path
        for i in range(1, len(path_1) - 1):
            idx_1 = np.where(path_2 == path_1[i])[0]
            if idx_1.size > 0:
                # Обмен хвостами пути между двумя родителями
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
            father, mother = np.random.choice(self.N, 2, replace=False)  # Случайный выбор двух родителей
            parent_1 = copy.deepcopy(self.population[father])
            parent_2 = copy.deepcopy(self.population[mother])
            if np.random.rand() < self.Pc:
                # Если выполняется вероятность скрещивания, обмен частями пути
                child_1, child_2 = self.exchange_solution(parent_1, parent_2)
                child_1 = self.correct_solution(child_1)  # Коррекция потомков
                child_2 = self.correct_solution(child_2)
                child_1.fitness = self.evaluate(child_1.path)  # Оценка потомков
                child_2.fitness = self.evaluate(child_2.path)
            else:
                child_1, child_2 = parent_1, parent_2  # Если нет скрещивания, потомки копируют родителей

            children.extend([child_1, child_2])

        if len(children) < self.N:
            children.append(copy.deepcopy(children[-1]))  # Добавление последнего решения при необходимости

        self.population = children  # Обновление популяции новыми потомками
    
    def mutation(self):
        # Процедура мутации для изменения путей в популяции
        for i in range(len(self.population)):
            if np.random.rand() < self.Pm:
                solution = self.population[i]
                mutation_point = np.random.randint(1, len(solution.path) - 1)  # Точка мутации

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
                solution.fitness = self.evaluate(solution.path)  # Оценка после мутации
                
    def selection(self):
        # Турнирный отбор для выбора решений в следующее поколение
        selected_population = []
        for _ in range(self.N):
            tournament_indices = np.random.randint(0, len(self.population), self.Ts)  # Выбор индексов для турнира
            tournament = [self.population[i] for i in tournament_indices]
            winner = min(tournament, key=lambda x: x.fitness)  # Выбор решения с наименьшей приспособленностью
            selected_population.append(copy.deepcopy(winner))
        self.population = selected_population  # Обновление популяции
    
    def compare_best(self):
        # Сравнение текущей популяции для нахождения лучших решений
        self.population.sort(key=lambda x: x.fitness)  # Сортировка популяции по приспособленности
        candidates = []
        for solution in self.population:
            if len(candidates) >= self.K:
                break
            if not any(np.array_equal(solution.path, candidate.path) for candidate in candidates):
                candidates.append(copy.deepcopy(solution))  # Добавление уникальных путей

        change_best = False
        for candidate in candidates:
            for id in range(len(self.best)):
                if (not any(np.array_equal(candidate.path, solution.path) for solution in self.best)) and candidate.fitness < self.best[id].fitness:
                    self.best[id] = copy.deepcopy(candidate)  # Обновление лучших решений
                    change_best = True
                    break
        if change_best == True:
            self.make_change_best()  # Обновление словаря лучших решений
    
    def make_change_best(self):
        # Обновление словаря путей (список вершин, ребер и весов путей)
        self.paths_dict[self.key][0] = [solution.path.tolist() for solution in self.best]
        self.paths_dict[self.key][1] = self.compute_edges_of_paths(self.paths_dict[self.key][0])
        self.paths_dict[self.key][2] = [float(solution.fitness) for solution in self.best]
        
    def show(self):
        # Отображение текущей популяции и их приспособленности
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
    
    def compute_shortest_paths(self, time_limit):
        # Основной цикл генетического алгоритма с временным ограничением
        start = time.time()  # Начало времени работы алгоритма
        self.reset_1()
        self.reset_2()
        for iteration in range(self.Max):
            time.sleep(0)  # Пауза для прерывания при необходимости
            self.crossover()
            self.mutation()
            self.selection()
            self.compare_best()
            self.reset_1()
            self.re_evaluate()
            end = time.time()  # Конец текущего итерации
            if end - start > time_limit:  # Прекращение выполнения, если превысили лимит времени
                break
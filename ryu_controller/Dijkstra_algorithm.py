MAX_VALUE = 10**10

class DijkstraAlgorithm:

    def __init__(self, weight_map):
        self.switches = list(weight_map.keys())
        self.weight_map = weight_map
        self.distance = {}
        self.previous = {}

    def compute_shortest_path(self, src, dst):
        if src not in self.switches or dst not in self.switches:
            return []

        self.distance = {vertex: MAX_VALUE for vertex in self.switches}
        self.previous = {vertex: None for vertex in self.switches}
        self.distance[src] = 0

        unvisited_vertices = self.switches.copy()

        while unvisited_vertices:
            current_vertex = self.find_nearest_vertex(unvisited_vertices)
            if current_vertex is None:
                break
            unvisited_vertices.remove(current_vertex)

            for neighbor, weight in self.weight_map.get(current_vertex, {}).items():
                if neighbor in unvisited_vertices:
                    new_distance = self.distance[current_vertex] + weight
                    if new_distance < self.distance[neighbor]:
                        self.distance[neighbor] = new_distance
                        self.previous[neighbor] = current_vertex
                    elif new_distance == self.distance[neighbor]:
                        if self.compare_lexicographically(current_vertex, self.previous[neighbor]):
                            self.previous[neighbor] = current_vertex

        return self.recover_path(dst)

    def find_nearest_vertex(self, unvisited):
        nearest_vertex = None
        min_distance = MAX_VALUE
        for vertex in unvisited:
            if self.distance[vertex] < min_distance:
                min_distance = self.distance[vertex]
                nearest_vertex = vertex
            elif self.distance[vertex] == min_distance:
                if nearest_vertex is None or vertex < nearest_vertex:
                    nearest_vertex = vertex
        return nearest_vertex

    def recover_path(self, dst):
        if self.distance[dst] == MAX_VALUE:
            return []

        path = []
        current_vertex = dst
        while current_vertex is not None:
            path.append(current_vertex)
            current_vertex = self.previous[current_vertex]
        return path[::-1]
    
    def compare_lexicographically(self, vertex_1, vertex_2):
        if vertex_1 is None:
            return False
        if vertex_2 is None:
            return True
        return vertex_1 < vertex_2
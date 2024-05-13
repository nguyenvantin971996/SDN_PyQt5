MAX_VALUE_1 = 10**10
MAX_VALUE_2= 10**20

class DijkstraAlgorithm:

    def __init__(self, weight_map, vertices):
        if not isinstance(weight_map, dict) or not isinstance(vertices, list):
            print("Invalid weight_map or vertices type. weight_map must be a dict and vertices must be a list.")

        self._vertices = vertices
        self._weight_map = weight_map
        self._distance = {}
        self._previous = {}

    def compute_shortest_path(self, src, dst):
        if src not in self._vertices or dst not in self._vertices:
            # print("src or dst not in vertices")
            return []

        self._distance = {vertex: MAX_VALUE_1 for vertex in self._vertices}
        self._previous = {vertex: None for vertex in self._vertices}
        self._distance[src] = 0

        unvisited_vertices = self._vertices.copy()

        while unvisited_vertices:
            current_vertex = self._find_nearest_vertex(unvisited_vertices)
            if current_vertex is None:
                break
            unvisited_vertices.remove(current_vertex)

            for neighbor, weight in self._weight_map.get(current_vertex, {}).items():
                if neighbor in unvisited_vertices:
                    new_distance = self._distance[current_vertex] + weight
                    if new_distance < self._distance[neighbor]:
                        self._distance[neighbor] = new_distance
                        self._previous[neighbor] = current_vertex

        return self._recover_path(dst)

    def _find_nearest_vertex(self, unvisited):
        nearest_vertex = None
        min_distance = MAX_VALUE_2
        for vertex in unvisited:
            if self._distance[vertex] < min_distance:
                min_distance = self._distance[vertex]
                nearest_vertex = vertex
        return nearest_vertex

    def _recover_path(self, dst):
        if self._previous[dst] is None:
            # print("No path to dst")
            return []

        path = []
        current_vertex = dst
        while current_vertex is not None:
            path.append(current_vertex)
            current_vertex = self._previous[current_vertex]
        return path[::-1]
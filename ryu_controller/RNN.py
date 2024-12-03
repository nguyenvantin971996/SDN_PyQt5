import numpy as np
from sklearn.preprocessing import StandardScaler

edges = [[1, 2], [1, 5], [1, 8], [2, 3], [3, 4], [3, 8], [3, 9], [4, 10], [5, 6], [6, 7], [6, 8], [6, 9], [7, 10], [9, 10]]

class RNN:
    def __init__(self, model,  weight_map, src=1, dst=10, K=4):
        self.model = model
        self.weight_map = weight_map
        self.src = src
        self.dst = dst
        self.K = K

        self.sc = StandardScaler()
        self.edges = edges

    def compute_shortest_paths(self):
        input_values = []
        for edge in self.edges:
            node1, node2 = edge
            input_values.append(float(self.weight_map[node1][node2]))
        
        input_values = np.array(input_values).reshape(-1, 1)
        input_values = self.sc.fit_transform(input_values).T
        input_data = np.repeat(input_values[:, np.newaxis, :], self.K, axis=1)

        pred = self.model.predict(input_data)
        pred = pred.round()

        paths_nodes = []
        paths_lengths = []

        for step in range(self.K):
            path_edges = []
            for i, edge in enumerate(self.edges):
                if pred[0, step, i] == 1:
                    path_edges.append(edge)
            print(f"Step {step + 1} - Edges selected: {path_edges}")

            path_nodes = []
            used_edges = []

            current_node = self.src
            path_nodes.append(current_node)

            while len(used_edges) < len(path_edges):
                edge_found = False
                for edge in path_edges:
                    if edge[0] == current_node and edge not in used_edges:
                        path_nodes.append(edge[1])
                        used_edges.append(edge)
                        current_node = edge[1]
                        edge_found = True
                        break
                    elif edge[1] == current_node and edge not in used_edges:
                        path_nodes.append(edge[0])
                        used_edges.append(edge)
                        current_node = edge[0]
                        edge_found = True
                        break

                if not edge_found:
                    print(f"Warning: Could not complete path in step {step + 1}. The path is broken.")
                    path_nodes = []
                    break

            if path_nodes:
                paths_nodes.append(path_nodes)
                path_length = sum([self.weight_map[node1].get(node2, 0.0) for node1, node2 in path_edges])
                paths_lengths.append(path_length)
            else:
                print(f"Step {step + 1}: No valid path was found.")
                paths_nodes.append([])
                paths_lengths.append(0)

        return paths_nodes, paths_lengths
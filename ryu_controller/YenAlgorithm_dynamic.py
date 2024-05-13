from YenAlgorithm import YenAlgorithm

class YenAlgorithm_dynamic:
    def __init__(self, port_monitor, paths_dict, key, K):
        self.port_monitor = port_monitor
        self.paths_dict = paths_dict
        self.weight_map = self.port_monitor.get_link_costs()

        self.key = key
        self.src = key[0]
        self.dst = key[2]

        self.K = K

    def compute_shortest_paths(self, time_limit):
        alg = YenAlgorithm(self.weight_map, self.src, self.dst, self.K)
        paths, paths_edges, pw = alg.compute_shortest_paths()
        self.paths_dict[self.key][0] = paths
        self.paths_dict[self.key][1] = paths_edges
        self.paths_dict[self.key][2] = pw
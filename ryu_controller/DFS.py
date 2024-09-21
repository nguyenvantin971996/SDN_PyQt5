class DFS:
    def __init__(self, weight_map, src, dst):
        self.weight_map = weight_map
        self.src = src
        self.dst = dst
        self.all_paths = []
    
    def find_all_paths(self):
        self.dfs(self.src, [self.src])
        return self.all_paths
    
    def dfs(self, current_node, path):
        if current_node == self.dst:
            self.all_paths.append(list(path))
            return
        
        for neighbor in self.weight_map[current_node].keys():
            if neighbor not in path:
                path.append(neighbor)
                self.dfs(neighbor, path)
                path.pop()

import copy
import numpy as np
class Results(object):
    def __init__(self, number_edges, edges, start_node, end_node, number_steps):
        self.number_edges = number_edges
        self.edges = edges
        self.start_node = start_node
        self.end_node = end_node
        self.number_steps = number_steps
    
    def cost_path(self,x,y):
        cost = 0
        path = []
        for i in range(self.number_edges):
            if y[i]==1:
                path.append(self.edges[i])
                cost+= x[i]
        if(len(path)!=0):
            path_2 = copy.deepcopy(path)
            path_nodes = [self.start_node]
            if(path[0][0]!= self.start_node):
                cost = 0
            else:
                path_nodes.append(path[0][1])
                del path_2[0]
                condition = True
                while(len(path_2)!=0 and condition):
                    condition = False
                    for i in range(len(path_2)):
                        if(path_nodes[-1] in path_2[i]):
                            path_2[i].remove(path_nodes[-1])
                            path_nodes.append(path_2[i][0])
                            path_2.pop(i)
                            condition = True
                            break
            if(path_nodes[-1]!=self.end_node or len(path_2)!=0):
                cost = 0
        else:
            cost = 0
        return cost
    
    def get_accuracy(self,pred, X, y):
        accuracy = np.zeros(self.number_steps+1)
        for i in range(pred.shape[0]):
            condition_1 = True
            paths = []
            for t in range(self.number_steps):
                output = list(pred[i][t])
                condition_2 = True
                for j in range(len(output)):
                    output[j] = round(output[j])
                if ((output in paths) or (self.cost_path(X[i],output) != self.cost_path(X[i],y[i][t]))):
                    condition_2 = False
                    condition_1 = False
                if condition_2:
                    accuracy[t] += 1
                paths.append(output)
            if condition_1:
                accuracy[self.number_steps] += 1
        accuracy = np.round(accuracy / pred.shape[0] * 100,2)
        return accuracy
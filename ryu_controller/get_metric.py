import json

def getMetric(fileName, metric='cost'):
    topoData = {}
    with open(fileName, 'r') as file:
        topoData = json.load(file)
    wMap = {}
    for item in topoData['switches']:
        wMap[item['id']] = {}
    for link in topoData['links']:
        if "Host" not in [link['start_node']['name_class'], link['end_node']['name_class']]:
            wMap[link['start_node']['id']][link['end_node']['id']] = link[metric]
            wMap[link['end_node']['id']][link['start_node']['id']] = link[metric]
    return wMap
import json

def getMetric(fileName, metric='cost'):
    topoData = {}
    with open(fileName, 'r') as file:
        topoData = json.load(file)
    wMap = {}
    for item in topoData['switches']:
        wMap[item['id']] = {}
    for link in topoData['links']:
        if "Host" not in [link['startNode']['nameClass'], link['endNode']['nameClass']]:
            wMap[link['startNode']['id']][link['endNode']['id']] = link[metric]
            wMap[link['endNode']['id']][link['startNode']['id']] = link[metric]
    return wMap
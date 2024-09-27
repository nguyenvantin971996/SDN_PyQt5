import json
import matplotlib.pyplot as plt
import os

font = {'size': 14}
plt.rc('font', **font)
colors = ['red', 'deepskyblue', 'lime', 'brown', 'orange', 'blue', 'black']
plt.rcParams['savefig.dpi'] = 200
plt.rcParams['savefig.bbox'] = 'tight'
plt.rcParams['savefig.directory'] = '/home/tin/SDN_PyQt5/result'

def makePlotChart(fileNames):
    fileNames = sorted(fileNames)
    try:
        result = {}
        maxThr = 0
        minThr = 1000000
        isUDP = False
        for i, fileName in enumerate(fileNames):
            try:
                with open(fileName, 'r') as file:
                    data = json.load(file)
            except Exception as e:
                print(f"Error reading file: {e}")
                return

            ends, throughputs, lossPercent, jitter = [], [], [], []
            fileName0 = os.path.basename(fileName)
            fileName = os.path.splitext(fileName0)[0]
            for item in data.get('intervals', []):
                ends.append(item['sum'].get('end', 0))
                throughputs.append(item['sum'].get('bits_per_second', 0) / 1e6)
                if "lost_packets" in item['sum']:
                    isUDP = True
                    lossPercent.append(item['sum'].get('lost_percent', 0))
                if "jitter_ms" in item['sum']:
                    jitter.append(item['sum'].get('jitter_ms', 0))
            if maxThr <= max(throughputs):
                maxThr = max(throughputs)
            if minThr >= min(throughputs):
                minThr = min(throughputs)
            result[fileName] = (ends, throughputs, lossPercent, jitter, colors[i])

        if isUDP:
            fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(10, 15))

            for i, fileName in enumerate(fileNames):
                fileName0 = os.path.basename(fileName)
                fileName = os.path.splitext(fileName0)[0]
                ax1.plot(result[fileName][0], result[fileName][1], marker='o', label=fileName, color=result[fileName][-1])
            ax1.legend(loc="upper right")
            ax1.set_ylabel('Throughput (Mbps)')
            ax1.grid()
            ax1.set_ylim(minThr * 0.5, maxThr * 1.2)

            for i, fileName in enumerate(fileNames):
                fileName0 = os.path.basename(fileName)
                fileName = os.path.splitext(fileName0)[0]
                ax2.plot(result[fileName][0], result[fileName][2], marker='o', label=fileName, color=result[fileName][-1])
            ax2.legend(loc="upper right")
            ax2.set_ylabel('Loss (%)')
            ax2.grid()

            for i, fileName in enumerate(fileNames):
                fileName0 = os.path.basename(fileName)
                fileName = os.path.splitext(fileName0)[0]
                ax3.plot(result[fileName][0], result[fileName][3], marker='o', label=fileName, color=result[fileName][-1])
            ax3.legend(loc="upper right")
            ax3.set_ylabel('Jitter (ms)')
            ax3.grid()
            fig.tight_layout()
            plt.show()
        else:
            fig, ax1 = plt.subplots(figsize=(10, 5))

            for i, fileName in enumerate(fileNames):
                fileName0 = os.path.basename(fileName)
                fileName = os.path.splitext(fileName0)[0]
                ax1.plot(result[fileName][0], result[fileName][1], marker='o', label=fileName, color=result[fileName][-1])
            ax1.legend(loc="upper right")
            ax1.set_ylabel('Throughput (Mbps)')
            ax1.set_xlabel('Time (seconds)')
            ax1.grid()
            ax1.set_ylim(minThr * 0.5, maxThr * 1.2)
            fig.tight_layout()
            plt.show()
    except:
        dataPerKey = {}
        fileLabels = [os.path.splitext(os.path.basename(fileName))[0] for i, fileName in enumerate(fileNames)]
        
        for idx, fileName in enumerate(fileNames):
            try:
                with open(fileName, 'r') as file:
                    data = json.load(file)
                    u = 0
                    for key, values in data.items():
                        if u % 2 == 0:
                            if key not in dataPerKey:
                                dataPerKey[key] = []
                            dataPerKey[key].append((values, fileLabels[idx]))
                        u += 1
            except Exception as e:
                print(f"Error reading file: {e}")
                return
        
        numKeys = len(dataPerKey)
        fig, axs = plt.subplots(numKeys, 1, figsize=(10, 5), squeeze=False)
        for i, (key, valuesList) in enumerate(dataPerKey.items()):
            ax = axs[i, 0]
            v = 0
            for j, (values, label) in enumerate(valuesList):
                v = len(values)
                ax.plot(range(1, v+1), values, marker='o', label=label, color=colors[j % len(colors)])
            ax.set_xticks(list(range(1, v+1)))
            ax.legend(loc="upper right")
            ax.set_title(f'{key}')
            ax.set_ylabel('Total cost of all updated paths')
            ax.set_xlabel('Time (seconds)')
            ax.grid()
        fig.tight_layout()
        plt.show()

import json
import matplotlib.pyplot as plt
import os

font = {'size': 10}
plt.rc('font', **font)
colors = ['red', 'deepskyblue', 'lime', 'brown', 'orange', 'blue', 'black', 'purple', 'yellow']
markers = [ '+', 's', '^', 'D', 'v', 'x','o', 'o', 'o']
linestyles = ['solid', 'dashed', 'dotted', 'solid', 'dashed', 'dotted', 'solid', 'dashed', 'dotted']
labels = ["ABC", "ACS", "AS", "BFA", "FA", "GA"]
plt.rcParams['savefig.dpi'] = 200
plt.rcParams['savefig.bbox'] = 'tight'
plt.rcParams['savefig.directory'] = '/home/tin/SDN_PyQt5/result'

def makePlotChart(fileNames):
    fileNames = sorted(fileNames)
    styles = {label: {'color': colors[i], 'marker': markers[i], 'linestyle': linestyles[i]} 
                  for i, label in enumerate(labels)}
    legend_lines = [None] * len(labels)
    legend_labels = [None] * len(labels)
    other_lines = []
    other_labels = []
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
                
                if "lost_packets" in item['streams'][0]:
                    isUDP = True
                    streamLosses = []
                    for stream in item['streams']:
                        packets_sent = stream.get('packets', 0)
                        lost_packets = stream.get('lost_packets', 0)

                        if packets_sent > 0:
                            calculated_loss = (lost_packets / packets_sent) * 100
                        else:
                            calculated_loss = 0

                        if packets_sent == 0 and lost_packets == 0:
                            calculated_loss = 100

                        streamLosses.append(calculated_loss)
                    
                    average_loss = sum(streamLosses) / len(streamLosses)
                    lossPercent.append(average_loss)
                
                if "jitter_ms" in item['streams'][0]:
                    avg_jitter = sum([stream.get('jitter_ms', 0) for stream in item['streams']]) / len(item['streams'])
                    jitter.append(avg_jitter)
            
            if maxThr <= max(throughputs):
                maxThr = max(throughputs)
            if minThr >= min(throughputs):
                minThr = min(throughputs)
            
            result[fileName] = (ends[:50], throughputs[1:51], lossPercent[1:51], jitter[1:51], colors[i])

        if isUDP:
            # fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(10, 15))
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 10))
            default_color_idx = len(labels)
            for i, fileName in enumerate(fileNames):
                fileName0 = os.path.basename(fileName)
                fileName = os.path.splitext(fileName0)[0]

                if fileName in styles:
                        style = styles[fileName]
                        line, = ax1.plot(result[fileName][0], result[fileName][1], 
                                        linewidth=2, linestyle=style['linestyle'], 
                                        marker=style['marker'], markersize=7, 
                                        label=fileName, color=style['color'])
                        label_idx = labels.index(fileName)
                        legend_lines[label_idx] = line
                        legend_labels[label_idx] = fileName
                else:
                    style = {'color': colors[default_color_idx], 'marker': markers[default_color_idx], 'linestyle': linestyles[default_color_idx]}
                    default_color_idx += 1

                    line, = ax1.plot(result[fileName][0], result[fileName][1], 
                                        linewidth=2, linestyle=style['linestyle'], 
                                        marker=style['marker'], markersize=7, 
                                        label=fileName, color=style['color'])
                    other_lines.append(line)
                    other_labels.append(fileName)
            ax1.legend(legend_lines + other_lines, legend_labels + other_labels, loc="upper right", ncol=3)
            ax1.set_ylabel('Throughput (Mbps)')
            ax1.set_xlabel('Time (seconds)')
            ax1.grid()
            ax1.set_ylim(minThr * 0.5, maxThr * 1.2)

            default_color_idx = len(labels)
            for i, fileName in enumerate(fileNames):
                fileName0 = os.path.basename(fileName)
                fileName = os.path.splitext(fileName0)[0]

                if fileName in styles:
                    style = styles[fileName]
                else:
                    style = {'color': colors[default_color_idx], 'marker': markers[default_color_idx], 'linestyle': linestyles[default_color_idx]}
                    default_color_idx += 1

                ax2.plot(result[fileName][0], result[fileName][2], 
                         linewidth=2, linestyle=style['linestyle'], 
                         marker=style['marker'], markersize=7, 
                         label=fileName, color=style['color'])
                
            ax2.legend(legend_lines + other_lines, legend_labels + other_labels, loc="upper right", ncol=3)
            ax2.set_ylabel('Loss (%)')
            ax2.set_xlabel('Time (seconds)')
            ax2.grid()

            # default_color_idx = len(labels)
            # for i, fileName in enumerate(fileNames):
            #     fileName0 = os.path.basename(fileName)
            #     fileName = os.path.splitext(fileName0)[0]
            #     if fileName in styles:
            #         style = styles[fileName]
            #     else:
            #         style = {'color': colors[default_color_idx], 'marker': markers[default_color_idx], 'linestyle': linestyles[default_color_idx]}
            #         default_color_idx += 1

            #     ax3.plot(result[fileName][0], result[fileName][3], 
            #              linewidth=2, linestyle=style['linestyle'], 
            #              marker=style['marker'], markersize=7, 
            #              label=fileName, color=style['color'])
            # ax3.legend(legend_lines + other_lines, legend_labels + other_labels, loc="upper right", ncol=3)
            # ax3.set_ylabel('Jitter (ms)')
            # ax3.set_xlabel('Time (seconds)')
            # ax3.grid()

            fig.tight_layout()
            plt.show()

        else:
            fig, ax1 = plt.subplots(figsize=(10, 5))

            default_color_idx = len(labels)
            for i, fileName in enumerate(fileNames):
                fileName0 = os.path.basename(fileName)
                fileName = os.path.splitext(fileName0)[0]

                if fileName in styles:
                        style = styles[fileName]
                        line, = ax1.plot(result[fileName][0], result[fileName][1], 
                                        linewidth=2, linestyle=style['linestyle'], 
                                        marker=style['marker'], markersize=7, 
                                        label=fileName, color=style['color'])
                        label_idx = labels.index(fileName)
                        legend_lines[label_idx] = line
                        legend_labels[label_idx] = fileName
                else:
                    style = {'color': colors[default_color_idx], 'marker': markers[default_color_idx], 'linestyle': linestyles[default_color_idx]}
                    default_color_idx += 1

                    line, = ax1.plot(result[fileName][0], result[fileName][1], 
                                        linewidth=2, linestyle=style['linestyle'], 
                                        marker=style['marker'], markersize=7, 
                                        label=fileName, color=style['color'])
                    other_lines.append(line)
                    other_labels.append(fileName)
            ax1.legend(legend_lines + other_lines, legend_labels + other_labels, loc="upper right", ncol=3)
            ax1.legend(loc="upper right")
            ax1.set_ylabel('Throughput (Mbps)')
            ax1.set_xlabel('Time (seconds)')
            ax1.grid()
            ax1.set_ylim(minThr * 0.5, maxThr * 1.2)

            fig.tight_layout()
            plt.show()

    except Exception as e:
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

        default_color_idx = len(labels)
        for i, (key, valuesList) in enumerate(dataPerKey.items()):
            ax = axs[i, 0]
            v = 0
            for j, (values, label) in enumerate(valuesList):
                v = len(values)
                if label in styles:
                    style = styles[label]
                    line, = ax.plot(range(1, v+1), values, linewidth=2, linestyle=style['linestyle'], 
                                    marker=style['marker'], markersize=7, label=label, color=style['color'])
                    label_idx = labels.index(label)
                    legend_lines[label_idx] = line
                    legend_labels[label_idx] = label
                else:
                    style = {'color': colors[default_color_idx], 'marker': markers[default_color_idx], 'linestyle': linestyles[default_color_idx]}
                    default_color_idx += 1
                    line, = ax.plot(range(1, v+1), values, linewidth=2, linestyle=style['linestyle'], 
                                    marker=style['marker'], markersize=7, label=label, color=style['color'])
                    other_lines.append(line)
                    other_labels.append(label)

                ax.plot(range(1, v+1), values, linewidth=2, linestyle=style['linestyle'], 
                        marker=style['marker'], markersize=7, label=label, color=style['color'])
            ax.set_xticks(list(range(1, v+1)))
            ax.legend(legend_lines + other_lines, legend_labels + other_labels, loc="upper right", ncol=3)
            ax.set_title(f'{key}')
            ax.set_ylabel('Total cost of all updated paths')
            ax.set_xlabel('Time (seconds)')
            ax.grid()
        fig.tight_layout()
        plt.show()

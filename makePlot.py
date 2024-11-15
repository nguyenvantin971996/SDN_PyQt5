import json
import matplotlib.pyplot as plt
import os
import random
import numpy as np
import sys
sys.path.append('../ryu_controller')
from ryu_controller.setting import PORT_PERIOD

font = {'size': 14}
plt.rc('font', **font)
# colors = ['red', 'deepskyblue', 'lime', 'brown', 'orange', 'blue', 'black', 'purple', 'orangered']
colors = ['red', 'deepskyblue', 'lime', 'brown', 'orange', 'blue', 'red', 'deepskyblue', 'lime']
markers = [ '+', 's', '^', 'D', 'v', 'x','o', 'v', 'x']
linestyles = ['solid', 'dashed', 'dotted', 'solid', 'dashed', 'dotted', 'solid', 'dashed', 'dotted']
labels = ["ABC", "ACS", "AS", "BFA", "FA", "GA"]

matplotlib_colors = list(plt.cm.colors.CSS4_COLORS)
matplotlib_markers = ['.', ',', 'o', 'v', '^', '<', '>', '1', '2', '3', '4', 's', 'p', '*', 'h', 'H', '+', 'x', 'D', 'd']
matplotlib_linestyles = ['-', '--', '-.', ':']

plt.rcParams['savefig.dpi'] = 200
plt.rcParams['savefig.bbox'] = 'tight'
plt.rcParams['savefig.directory'] = '/home/tin/SDN_PyQt5/result'

def makePlotChart(fileNames):
    fileNames = sorted(fileNames)
    styles = {label: {'color': colors[i % len(colors)], 
                  'marker': markers[i % len(markers)], 
                  'linestyle': linestyles[i % len(linestyles)]} 
                  for i, label in enumerate(labels)}
    legend_lines = [None] * len(labels)
    legend_labels = [None] * len(labels)
    other_lines = []
    other_labels = []
    n_cols = None
    if len(fileNames)%3==0:
        if len(fileNames)==3:
            n_cols = 1
        else:
            n_cols = 3
    else:
        n_cols = 2
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
                    average_jitter = sum([stream.get('jitter_ms', 0) for stream in item['streams']]) / len(item['streams'])
                    jitter.append(average_jitter)
            
            if maxThr <= max(throughputs):
                maxThr = max(throughputs)
            if minThr >= min(throughputs):
                minThr = min(throughputs)
            
            result[fileName] = (ends, throughputs, lossPercent, jitter)
        if isUDP:
            # fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(10, 15))
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 10))
            default_color_idx = len(labels)
            for i, fileName in enumerate(fileNames):
                fileName0 = os.path.basename(fileName)
                fileName = os.path.splitext(fileName0)[0]
                avg_throughput = np.mean(result[fileName][1])
                avg_loss = np.mean(result[fileName][2])
                avg_throughput_str = f"{avg_throughput:.1f}"
                avg_loss_str = f"{avg_loss:.1f}" 
                # label_to_plot = f"{fileName} (Throughput={avg_throughput_str} Mbps, Loss={avg_loss_str}%)"
                label_to_plot_throughtput = f"{fileName} (Throughput={avg_throughput_str} Mbps)"
                label_to_plot_loss= f"{fileName} (Loss={avg_loss_str}%)"
                if fileName in styles:
                    style = styles[fileName]
                    line, = ax1.plot(result[fileName][0], result[fileName][1], 
                                    linewidth=2, linestyle=style['linestyle'], 
                                    marker=style['marker'], markersize=7, color=style['color'])
                    label_idx = labels.index(fileName)
                    legend_lines[label_idx] = line
                    legend_labels[label_idx] = [label_to_plot_throughtput, label_to_plot_loss]
                    
                else:
                    if default_color_idx < len(colors):
                        style = {'color': colors[default_color_idx % len(colors)], 
                                'marker': markers[default_color_idx % len(markers)], 
                                'linestyle': linestyles[default_color_idx % len(linestyles)]}
                        default_color_idx += 1
                    else:
                        style = {'color': random.choice(matplotlib_colors), 
                        'marker': random.choice(matplotlib_markers), 
                        'linestyle': random.choice(matplotlib_linestyles)}

                    line, = ax1.plot(result[fileName][0], result[fileName][1], 
                                        linewidth=2, linestyle=style['linestyle'], 
                                        marker=style['marker'], markersize=7, color=style['color'])
                    other_lines.append(line)
                    other_labels.append([label_to_plot_throughtput, label_to_plot_loss])
                    styles[fileName] = style

            valid_legend_lines = [line for line in legend_lines if line is not None]
            combined_lines = valid_legend_lines + other_lines

            valid_legend_labels_throughput = [label[0] for line, label in zip(legend_lines, legend_labels) if line is not None]
            other_labels_throughput = [label[0] for label in other_labels]

            valid_legend_labels_loss = [label[1] for line, label in zip(legend_lines, legend_labels) if line is not None]
            other_labels_loss = [label[1] for label in other_labels]

            combined_labels_throughput = valid_legend_labels_throughput + other_labels_throughput
            combined_labels_loss = valid_legend_labels_loss + other_labels_loss

            ax1.legend(combined_lines, combined_labels_throughput, loc="upper right", ncol=n_cols)
            ax1.set_ylabel('Throughput (Mbps)')
            ax1.set_xlabel('Time (seconds)')
            ax1.grid()
            ax1.set_ylim(minThr * 0.5, maxThr * 1.4)

            for i, fileName in enumerate(fileNames):
                fileName0 = os.path.basename(fileName)
                fileName = os.path.splitext(fileName0)[0]

                style = styles[fileName]

                ax2.plot(result[fileName][0], result[fileName][2], 
                         linewidth=2, linestyle=style['linestyle'], 
                         marker=style['marker'], markersize=7, 
                         label=fileName, color=style['color'])
                
            ax2.legend(combined_lines, combined_labels_loss, loc="upper right", ncol=n_cols)
            ax2.set_ylabel('Packet loss rate (%)')
            ax2.set_xlabel('Time (seconds)')
            ax2.grid()

            # for i, fileName in enumerate(fileNames):
            #     fileName0 = os.path.basename(fileName)
            #     fileName = os.path.splitext(fileName0)[0]
            #     style = styles[fileName]

            #     ax3.plot(result[fileName][0], result[fileName][3], 
            #              linewidth=2, linestyle=style['linestyle'], 
            #              marker=style['marker'], markersize=7, 
            #              label=fileName, color=style['color'])
            # ax3.legend(combined_lines, combined_labels, loc="upper right", ncol=n_cols)
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
                    if default_color_idx < len(colors):
                        style = {'color': colors[default_color_idx % len(colors)], 
                                'marker': markers[default_color_idx % len(markers)], 
                                'linestyle': linestyles[default_color_idx % len(linestyles)]}
                        default_color_idx += 1
                    else:
                        style = {'color': random.choice(matplotlib_colors), 
                        'marker': random.choice(matplotlib_markers), 
                        'linestyle': random.choice(matplotlib_linestyles)}

                    line, = ax1.plot(result[fileName][0], result[fileName][1], 
                                        linewidth=2, linestyle=style['linestyle'], 
                                        marker=style['marker'], markersize=7, 
                                        label=fileName, color=style['color'])
                    other_lines.append(line)
                    other_labels.append(fileName)
            valid_legend_lines = [line for line in legend_lines if line is not None]
            valid_legend_labels = [label for line, label in zip(legend_lines, legend_labels) if line is not None]

            combined_lines = valid_legend_lines + other_lines
            combined_labels = valid_legend_labels + other_labels

            if combined_lines and combined_labels:
                ax1.legend(combined_lines, combined_labels, loc="upper right", ncol=n_cols)
            ax1.legend(loc="upper right")
            ax1.set_ylabel('Throughput (Mbps)')
            ax1.set_xlabel('Time (seconds)')
            ax1.grid()
            ax1.set_ylim(minThr * 0.5, maxThr * 1.2)

            fig.tight_layout()
            plt.show()

    except Exception as e:
        dataPerFile = {}
        fileLabels = [os.path.splitext(os.path.basename(fileName))[0] for fileName in fileNames]

        for idx, fileName in enumerate(fileNames):
            try:
                with open(fileName, 'r') as file:
                    data = json.load(file)
                    dataPerFile[fileLabels[idx]] = data
            except Exception as e:
                print(f"Error reading file {fileName}: {e}")
                continue

        fig, ax = plt.subplots(figsize=(10, 5))

        default_color_idx = len(labels)

        for label, values in dataPerFile.items():
            moments = [PORT_PERIOD*t for t in range(len(values))]
            if default_color_idx < len(colors):
                style = {
                    'color': colors[default_color_idx % len(colors)], 
                    'marker': markers[default_color_idx % len(markers)], 
                    'linestyle': linestyles[default_color_idx % len(linestyles)]
                }
                default_color_idx += 1
            else:
                style = {
                    'color': random.choice(matplotlib_colors), 
                    'marker': random.choice(matplotlib_markers), 
                    'linestyle': random.choice(matplotlib_linestyles)
                }
            ax.plot(moments, values, linewidth=2, 
                    linestyle=style['linestyle'], marker=style['marker'], 
                    markersize=7, label=label, color=style['color'])

        ax.set_ylabel('Load balancing index (LBI)')
        ax.set_xlabel('Time (seconds)')
        ax.legend(loc="upper center", ncol=n_cols)
        ax.grid()
        fig.tight_layout()
        plt.show()


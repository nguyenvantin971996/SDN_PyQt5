import json
import matplotlib.pyplot as plt
import os
import glob  # Import the glob module

font = {'size': 11}
plt.rc('font', **font)

def makePlot(directory, save_plot=False):
    # Search for all .json files in the given directory
    fileNames = glob.glob(os.path.join(directory, '*.json'))
    data_per_key = {}
    colors = ['green', 'red', 'blue', 'cyan', 'magenta']
    file_labels = [os.path.splitext(os.path.basename(fileName))[0] for fileName in fileNames]  # Extract base names
    
    # Load data from all files
    for idx, fileName in enumerate(fileNames):
        try:
            with open(fileName, 'r') as file:
                data = json.load(file)
                u = 0
                for key, values in data.items():
                    if u % 2 == 0:
                        if key not in data_per_key:
                            data_per_key[key] = []
                        data_per_key[key].append((values, file_labels[idx]))  # Pair values with file label
                    u += 1
        except Exception as e:
            print(f"Error reading file: {e}")
            return
    
    # Create a subplot for each key
    num_keys = len(data_per_key)
    fig, axs = plt.subplots(num_keys, 1, figsize=(10, 12), squeeze=False)
    
    for i, (key, values_list) in enumerate(data_per_key.items()):
        ax = axs[i, 0]  # Adjust for multi-subplot array
        for j, (values, label) in enumerate(values_list):
            ax.plot(values[:20], marker='o', label=label, color=colors[j % len(colors)])  # Use label from file basename
        ax.legend(loc="upper right")
        ax.set_title(f'{key}')
        ax.set_ylabel('CD')
        ax.grid(True, which='major', linestyle='--')
    
    fig.tight_layout()  # Adjusts the layout

    if save_plot:
        plt.savefig("comparison_plot.png")

    plt.show()

# Example usage
directory = '/home/tin/SDN_PyQt5/result/'
makePlot(directory)
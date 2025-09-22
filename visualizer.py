import re
import matplotlib.pyplot as plt
from collections import Counter
from datetime import datetime
import numpy as np

def count_log_events(log_file='log.txt'):
    patterns = {
        'File CREATED': r'File CREATED:',
        'File DELETED': r'File DELETED:',
        'File MODIFIED': r'File MODIFIED:',
        'File RENAMED': r'File RENAMED:',
        'Directory CREATED': r'Directory CREATED:',
        'Directory DELETED': r'Directory DELETED:',
        'Directory RENAMED': r'Directory RENAMED:'
    }

    counts = Counter()
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                for label, pattern in patterns.items():
                    if re.search(pattern, line):
                        counts[label] += 1
    except FileNotFoundError:
        print("Log file not found.")
    return counts


def visualize_log_counts_horizontal(counts):
    try:
        labels = list(counts.keys())
        values = list(counts.values())
        y = np.arange(len(labels))

        norm = plt.Normalize(min(values), max(values))
        colors = plt.cm.viridis(norm(values))

        fig, ax = plt.subplots(figsize=(12, 6))
        bars = ax.barh(y, values, color=colors, edgecolor='black', linewidth=1)

        ax.set_yticks(y)
        ax.set_yticklabels(labels, fontsize=12)
        ax.set_title('Summary of File and Directory Operations', fontsize=16, weight='bold')
        ax.set_xlabel('Count', fontsize=14)
        ax.set_ylabel('Operation Type', fontsize=14)
        ax.grid(axis='x', linestyle='--', alpha=0.3)

        for bar in bars:
            width = bar.get_width()
            ax.text(width - (width * 0.05), bar.get_y() + bar.get_height()/2,
                    f'{int(width)}', ha='right', va='center', color='white', fontsize=11, weight='bold')

        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        filename = f"log_chart_horizontal_{timestamp}.png"
        plt.tight_layout()
        plt.savefig(filename, dpi=300)
        print(f" Horizontal chart saved successfully as: {filename}")
        plt.show()

    except Exception as e:
        print(f" Error generating horizontal chart: {e}")
import json
import numpy as np
import matplotlib.pyplot as plt

def load_data(jsonfile):
    with open(jsonfile, 'r') as fh:
        raw_data = fh.read()
        data = json.loads(raw_data)
        return data


def plot(data):
    categories = []
    success_counts = []
    failure_counts = []
    pass_rates = []

    for provider, regions in data.items():
        for region, stats in regions.items():
            categories.append(f"{provider.upper()} - {region}")
            success_counts.append(stats.get("success", 0))
            failure_counts.append(stats.get("failure", 0))
            pass_rates.append(stats.get("pass_rate", 0.0))

    x = np.arange(len(categories))
    bar_width = 0.4

    fig, ax1 = plt.subplots(figsize=(12, 6))

    ax1.bar(x - bar_width / 2, success_counts, bar_width, label="Success", color="green")
    ax1.bar(x + bar_width / 2, failure_counts, bar_width, label="Failure", color="red")

    ax1.set_xlabel("Regions")
    ax1.set_ylabel("Counts", color="black")
    ax1.set_title("HCO CI: Success, Failure, and Pass Rates by Region")
    ax1.set_xticks(x)
    ax1.set_xticklabels(categories, rotation=45, ha="right")
    ax1.legend(loc="upper left")

    ax2 = ax1.twinx()
    ax2.plot(x, pass_rates, color="blue", marker="o", label="Pass Rate (%)")
    ax2.set_ylabel("Pass Rate (%)", color="blue")
    ax2.tick_params(axis="y", labelcolor="blue")
    ax2.set_ylim(0, 100)

    ax2.legend(loc="upper right")

    plt.tight_layout()
    plt.show()


def main():
    data = load_data('results_with_percent.json')
    plot(data)


if __name__ == '__main__':
    main()
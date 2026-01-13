# ============================================================
# Publication-Quality Visualization Script (Refined)
# For multispectral water body dataset (Landsat + Sentinel-2)
# ============================================================

import os
import rasterio
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from collections import defaultdict

# Try to use seaborn for better aesthetics
try:
    import seaborn as sns
    sns.set_context("paper")
    sns.set_style("ticks")
except ImportError:
    pass

# ======================
# User Configuration
# ======================

CONFIG = {
    "SCENE_DIR": r"D:\A_DATA\scene",
    "TRUTH_DIR": r"D:\A_DATA\truth",
    # Update sample names to match your actual file list if needed
    "SAMPLE_SCENES": [
        "I8_scene_12.tif",
        "S2A_L2A_20190314_N0211_R008_S3.tif" 
    ],
    "OUTPUT_DIR": r"D:\A_DATA\figures",
    "DPI": 300,
    "FONT_FAMILY": "Arial", # Suggested for papers
    "FONT_SIZE": 10
}

# ======================
# Utility Functions
# ======================

def setup_plot_style():
    """Configure matplotlib for publication standards."""
    plt.rcParams['font.family'] = CONFIG["FONT_FAMILY"]
    plt.rcParams['font.size'] = CONFIG["FONT_SIZE"]
    plt.rcParams['axes.titlesize'] = CONFIG["FONT_SIZE"] + 2
    plt.rcParams['axes.labelsize'] = CONFIG["FONT_SIZE"]
    plt.rcParams['xtick.labelsize'] = CONFIG["FONT_SIZE"]
    plt.rcParams['ytick.labelsize'] = CONFIG["FONT_SIZE"]
    os.makedirs(CONFIG["OUTPUT_DIR"], exist_ok=True)

def detect_satellite(fname):
    """
    Identify satellite type based on specific naming conventions.
    Rules:
    - I5_... -> Landsat-5
    - I7_... -> Landsat-7
    - I8_... -> Landsat-8
    - I9_... -> Landsat-9
    - S2...  -> Sentinel-2
    """
    # Remove _truth suffix if present to check the original ID
    clean_name = fname.replace("_truth.tif", "")
    
    if clean_name.startswith("I5"):
        return "Landsat-5"
    elif clean_name.startswith("I7"):
        return "Landsat-7"
    elif clean_name.startswith("I8"):
        return "Landsat-8"
    elif clean_name.startswith("I9"):
        return "Landsat-9"
    elif clean_name.startswith("S2"):
        return "Sentinel-2"
    else:
        return "Other"

def read_multiband_image(path):
    """Read image and apply 2%-98% percentile stretching for visualization."""
    try:
        with rasterio.open(path) as src:
            # Read RGB bands (Assuming bands 1,2,3 are R,G,B or similar visible)
            img = src.read([1, 2, 3]) 
            img = np.transpose(img, (1, 2, 0))
            
            # Robust normalization
            p2, p98 = np.percentile(img, (2, 98))
            img = np.clip(img, p2, p98)
            img = (img - p2) / (p98 - p2 + 1e-6)
            return np.clip(img, 0, 1)
    except Exception as e:
        print(f"Warning: Could not read image {path}: {e}")
        return None

def read_label(path):
    """Read binary mask."""
    try:
        with rasterio.open(path) as src:
            return src.read(1)
    except:
        return None

# ======================
# Statistics Calculation
# ======================

def calculate_dataset_stats():
    """
    Iterate strictly through TRUTH_DIR to ensure 1-to-1 matching.
    Returns:
        - sat_pixel_counts: Total pixels per satellite type
        - sat_scene_counts: Number of images per satellite type
        - water_counts: Global Water vs Non-Water pixel counts
        - water_ratios: List of water ratios per image
    """
    sat_pixel_counts = defaultdict(int)
    sat_scene_counts = defaultdict(int)
    water_counts = {"Water": 0, "Non-water": 0}
    water_ratios = []

    print("Scanning dataset statistics...")
    
    truth_files = [f for f in os.listdir(CONFIG["TRUTH_DIR"]) if f.endswith("_truth.tif")]
    
    if not truth_files:
        print("Error: No *_truth.tif files found in TRUTH_DIR!")
        return None, None, None, None

    for f in truth_files:
        path = os.path.join(CONFIG["TRUTH_DIR"], f)
        
        # 1. Identify Satellite
        sat_type = detect_satellite(f)
        sat_scene_counts[sat_type] += 1
        
        # 2. Read Meta and Label
        try:
            with rasterio.open(path) as src:
                # Use metadata for shape to avoid reading full array if possible
                h, w = src.height, src.width
                total_pixels = h * w
                sat_pixel_counts[sat_type] += total_pixels
                
                # Read actual data for water counts
                lbl = src.read(1)
                w_pix = np.sum(lbl == 1)
                
                water_counts["Water"] += int(w_pix)
                water_counts["Non-water"] += int(total_pixels - w_pix)
                water_ratios.append(w_pix / total_pixels)
        except Exception as e:
            print(f"Skipping {f}: {e}")

    return sat_pixel_counts, sat_scene_counts, water_counts, water_ratios

# ======================
# Plotting Functions
# ======================

def plot_combined_pie_charts(sat_pixels, water_counts):
    """Fig 1: Two pie charts merged (Pixel Dist + Water/Non-Water)."""
    fig, axes = plt.subplots(1, 2, figsize=(11, 5))
    
    # Colors
    colors_sat = ['#4c72b0', '#55a868', '#c44e52', '#8172b3', '#ccb974'] # Muted
    colors_water = ['#3498db', '#95a5a6'] # Blue / Grey

    # --- Left: Satellite Pixel Distribution ---
    labels_sat = sorted(list(sat_pixels.keys())) # Sort for consistency
    values_sat = [sat_pixels[k] for k in labels_sat]
    
    axes[0].pie(values_sat, labels=labels_sat, autopct="%.1f%%", 
                startangle=90, pctdistance=0.85, colors=colors_sat,
                wedgeprops=dict(width=0.4, edgecolor='w'))
    axes[0].set_title("(a) Pixel Contribution by Satellite", y=-0.05, fontweight='bold')

    # --- Right: Water Distribution ---
    labels_w = list(water_counts.keys())
    values_w = list(water_counts.values())
    
    axes[1].pie(values_w, labels=labels_w, autopct="%.1f%%", 
                startangle=140, pctdistance=0.85, colors=colors_water,
                wedgeprops=dict(width=0.4, edgecolor='w'))
    axes[1].set_title("(b) Global Pixel Class Distribution", y=-0.05, fontweight='bold')

    plt.tight_layout()
    save_path = os.path.join(CONFIG["OUTPUT_DIR"], "Fig1_Distribution_Pies.pdf")
    plt.savefig(save_path, dpi=CONFIG["DPI"], bbox_inches='tight')
    plt.savefig(save_path.replace(".pdf", ".png"), dpi=CONFIG["DPI"])
    print(f"[Saved] {save_path}")
    plt.close()

def plot_scene_counts_bar(sat_scene_counts):
    """Fig 2: Bar chart showing number of images per satellite."""
    fig, ax = plt.subplots(figsize=(7, 5))
    
    labels = sorted(list(sat_scene_counts.keys()))
    values = [sat_scene_counts[k] for k in labels]
    
    # Bar plot
    bars = ax.bar(labels, values, color='#4c72b0', edgecolor='black', alpha=0.8, width=0.6)
    
    # Labels and Title
    ax.set_ylabel("Number of Scenes")
    ax.set_title("Dataset Composition by Scene Count")
    
    # Add count labels on top of bars
    for bar in bars:
        height = bar.get_height()
        ax.annotate(f'{height}',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3),  # 3 points vertical offset
                    textcoords="offset points",
                    ha='center', va='bottom', fontweight='bold')
    
    # Remove top and right spines for cleaner look
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.grid(axis='y', linestyle='--', alpha=0.3)

    plt.tight_layout()
    save_path = os.path.join(CONFIG["OUTPUT_DIR"], "Fig2_Scene_Counts.pdf")
    plt.savefig(save_path, dpi=CONFIG["DPI"], bbox_inches='tight')
    plt.savefig(save_path.replace(".pdf", ".png"), dpi=CONFIG["DPI"])
    print(f"[Saved] {save_path}")
    plt.close()

def plot_samples():
    """Fig 3: Visual samples with correct matching."""
    num_samples = len(CONFIG["SAMPLE_SCENES"])
    fig = plt.figure(figsize=(8, 4 * num_samples))
    gs = gridspec.GridSpec(num_samples, 2, width_ratios=[1, 1], wspace=0.05, hspace=0.2)

    for i, scene_name in enumerate(CONFIG["SAMPLE_SCENES"]):
        # Construct paths
        img_path = os.path.join(CONFIG["SCENE_DIR"], scene_name)
        # Truth name logic: name.tif -> name_truth.tif
        truth_name = scene_name.replace(".tif", "_truth.tif")
        lbl_path = os.path.join(CONFIG["TRUTH_DIR"], truth_name)

        img = read_multiband_image(img_path)
        lbl = read_label(lbl_path)

        # Skip if file not found
        if img is None or lbl is None:
            print(f"Skipping sample {scene_name} (File not found)")
            continue

        # Plot Image
        ax1 = plt.subplot(gs[i, 0])
        ax1.imshow(img)
        ax1.axis("off")
        ax1.text(0.02, 0.98, f"Sample {i+1} (RGB)", transform=ax1.transAxes,
                 color='white', fontweight='bold', va='top', bbox=dict(facecolor='black', alpha=0.5, pad=2))

        # Plot Label
        ax2 = plt.subplot(gs[i, 1])
        ax2.imshow(lbl, cmap="Blues", interpolation='nearest')
        ax2.axis("off")
        ax2.text(0.02, 0.98, "Ground Truth", transform=ax2.transAxes,
                 color='black', fontweight='bold', va='top', bbox=dict(facecolor='white', alpha=0.7, pad=2))

    save_path = os.path.join(CONFIG["OUTPUT_DIR"], "Fig3_Visual_Samples.pdf")
    plt.savefig(save_path, dpi=CONFIG["DPI"], bbox_inches='tight')
    plt.savefig(save_path.replace(".pdf", ".png"), dpi=CONFIG["DPI"])
    print(f"[Saved] {save_path}")
    plt.close()

def plot_boxplot(ratios):
    """Fig 4: Water ratio distribution boxplot."""
    plt.figure(figsize=(6, 5))
    
    boxprops = dict(linestyle='-', linewidth=1.5, color='#4c72b0')
    medianprops = dict(linestyle='-', linewidth=2, color='#c44e52')
    flierprops = dict(marker='o', markerfacecolor='gray', markersize=4, alpha=0.5)

    plt.boxplot(ratios, vert=True, patch_artist=False,
                boxprops=boxprops, medianprops=medianprops, flierprops=flierprops,
                widths=0.4)
    
    plt.ylabel("Water Pixel Ratio (0-1)")
    plt.title("Distribution of Water Coverage per Scene")
    plt.grid(axis='y', linestyle='--', alpha=0.5)
    plt.xticks([])

    save_path = os.path.join(CONFIG["OUTPUT_DIR"], "Fig4_Water_Ratio_Box.pdf")
    plt.savefig(save_path, dpi=CONFIG["DPI"], bbox_inches='tight')
    plt.savefig(save_path.replace(".pdf", ".png"), dpi=CONFIG["DPI"])
    print(f"[Saved] {save_path}")
    plt.close()

# ======================
# Main Execution
# ======================

def main():
    setup_plot_style()
    
    # 1. Compute Stats
    sat_pixels, sat_scenes, water_counts, ratios = calculate_dataset_stats()
    
    if sat_pixels is None:
        return

    # 2. Generate Figures
    print("\n--- Generating Figures ---")
    
    # Fig 1: Pie Charts
    if sat_pixels:
        plot_combined_pie_charts(sat_pixels, water_counts)
    
    # Fig 2: Scene Counts Bar Chart (New Request)
    if sat_scenes:
        plot_scene_counts_bar(sat_scenes)

    # Fig 3: Samples
    plot_samples()

    # Fig 4: Boxplot
    if ratios:
        plot_boxplot(ratios)

    print("\nAll tasks completed successfully.")

if __name__ == "__main__":
    main()
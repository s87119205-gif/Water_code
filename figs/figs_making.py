# ============================================================
# Publication-Quality Visualization Script (Fixed RGB)
# ============================================================

import os
import rasterio
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.ticker as mtick
from collections import defaultdict

# Optional: Seaborn style
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
    "SAMPLE_SCENES": [
        "I8_scene_12.tif",
        "S2A_L2A_20190314_N0211_R008_S3.tif" 
    ],
    "OUTPUT_DIR": r"D:\A_DATA\figures",
    "DPI": 300,
    "FONT_FAMILY": "Arial",
    "FONT_SIZE": 10
}

# ======================
# Band Configuration
# ======================

def get_rgb_bands(satellite_type):
    """
    Returns the band indices for (Red, Green, Blue) based on sensor type.
    Rasterio uses 1-based indexing.
    """
    # Map: Satellite -> [Red_Index, Green_Index, Blue_Index]
    BAND_MAP = {
        "Sentinel-2": [4, 3, 2], # S2: B4(Red), B3(Green), B2(Blue)
        "Landsat-8":  [3, 2, 1], # L8: B5(Red), B4(Green), B3(Blue)
        "Landsat-9":  [5, 4, 3], # L9: B5(Red), B4(Green), B3(Blue)
        "Landsat-5":  [3, 2, 1], # L5: B3(Red), B2(Green), B1(Blue)
        "Landsat-7":  [3, 2, 1], # L7: B3(Red), B2(Green), B1(Blue)
        "Other":      [1, 2, 3]  # Fallback
    }
    return BAND_MAP.get(satellite_type, [1, 2, 3])

def detect_satellite(fname):
    """Detect satellite from filename."""
    clean_name = fname.replace("_truth.tif", "")
    if clean_name.startswith("I5"): return "Landsat-5"
    elif clean_name.startswith("I7"): return "Landsat-7"
    elif clean_name.startswith("I8"): return "Landsat-8"
    elif clean_name.startswith("I9"): return "Landsat-9"
    elif clean_name.startswith("S2"): return "Sentinel-2"
    else: return "Other"

# ======================
# I/O Functions
# ======================

def read_multiband_image(path, satellite_type):
    """
    Reads specific RGB bands and applies robust stretching.
    """
    try:
        rgb_indices = get_rgb_bands(satellite_type)
        
        with rasterio.open(path) as src:
            # Check if file has enough bands
            if src.count < max(rgb_indices):
                print(f"Warning: {path} has {src.count} bands, but tried to read {rgb_indices}")
                # Fallback to first 3 bands if indices are out of bounds
                img = src.read([1, 2, 3])
            else:
                img = src.read(rgb_indices) # Read (R, G, B) order
            
            img = np.transpose(img, (1, 2, 0)) # (H, W, Bands)
            
            # --- Robust Percentile Stretching ---
            # Exclude 0 values (often NoData) from percentile calculation
            valid_mask = img > 0
            if valid_mask.any():
                p2 = np.percentile(img[valid_mask], 2)
                p98 = np.percentile(img[valid_mask], 98)
            else:
                p2, p98 = 0, 1
            
            img = np.clip(img, p2, p98)
            img = (img - p2) / (p98 - p2 + 1e-6)
            
            return np.clip(img, 0, 1)
    except Exception as e:
        print(f"Error reading {path}: {e}")
        return None

def read_label(path):
    try:
        with rasterio.open(path) as src:
            return src.read(1)
    except:
        return None

# ======================
# Statistics (Unchanged)
# ======================
def calculate_dataset_stats():
    sat_pixel_counts = defaultdict(int)
    sat_scene_counts = defaultdict(int)
    water_counts = {"Water": 0, "Non-water": 0}
    water_ratios = []
    
    # [Same logic as previous, iterating TRUTH_DIR]
    print("Scanning dataset statistics...")
    truth_files = [f for f in os.listdir(CONFIG["TRUTH_DIR"]) if f.endswith("_truth.tif")]
    
    for f in truth_files:
        path = os.path.join(CONFIG["TRUTH_DIR"], f)
        sat_type = detect_satellite(f)
        sat_scene_counts[sat_type] += 1
        try:
            with rasterio.open(path) as src:
                sat_pixel_counts[sat_type] += src.width * src.height
                lbl = src.read(1)
                w_pix = np.sum(lbl == 1)
                water_counts["Water"] += int(w_pix)
                water_counts["Non-water"] += int(lbl.size - w_pix)
                water_ratios.append(w_pix / lbl.size)
        except: pass
        
    return sat_pixel_counts, sat_scene_counts, water_counts, water_ratios

# ======================
# Plotting
# ======================

def plot_combined_statistics(sat_pixels, sat_scenes, water_counts):
    """
    Fig 1 Revised V2:
    - Fixed missing values on the right chart.
    - Fixed excessive gap between charts and captions.
    - Optimized label positions.
    """
    # Create figure with a tighter layout ratio
    fig, axes = plt.subplots(1, 2, figsize=(12, 6))
    
    # --- Color Palette ---
    sat_keys = sorted(list(sat_pixels.keys()))
    colors_sat = ['#4c72b0', '#55a868', '#c44e52', '#8172b3', '#ccb974', '#64b5cd'][:len(sat_keys)]
    colors_water = ['#3498db', '#95a5a6'] 

    # ===================================================
    # SUBPLOT 1: Satellite Composition (Double Donut)
    # ===================================================
    ax1 = axes[0]
    
    vals_outer = [sat_pixels[k] for k in sat_keys]
    vals_inner = [sat_scenes[k] for k in sat_keys]
    
    # --- Outer Ring (Pixel Ratio) ---
    wedges_o, texts_o, autotexts_o = ax1.pie(
        vals_outer, radius=1.0, 
        colors=colors_sat,
        wedgeprops=dict(width=0.3, edgecolor='white', linewidth=1.5),
        autopct='%.1f%%', 
        pctdistance=0.85, # Center of the outer ring (0.7 to 1.0)
        startangle=90
    )
    
    # --- Inner Ring (Scene Counts) ---
    def make_autopct(values):
        def my_autopct(pct):
            total = sum(values)
            val = int(round(pct*total/100.0))
            return '{v:d}'.format(v=val)
        return my_autopct

    wedges_i, texts_i, autotexts_i = ax1.pie(
        vals_inner, radius=0.68, 
        colors=colors_sat,
        wedgeprops=dict(width=0.3, edgecolor='white', linewidth=1.5),
        autopct=make_autopct(vals_inner),
        pctdistance=0.78, # Center of the inner ring (0.38 to 0.68)
        startangle=90
    )

    # Style Labels
    plt.setp(autotexts_o, size=9, weight="bold", color="white")
    plt.setp(autotexts_i, size=9, weight="bold", color="white")

    # Legend
    ax1.legend(wedges_o, sat_keys, title="Satellite Platform",
               loc="center", bbox_to_anchor=(0.5, 0.5),
               fontsize=9, frameon=False, alignment='center')

    # Annotations (Top Left)
    # text coords relative to axes
    ax1.text(-0.05, 1.02, "Outer Ring: Pixel Contribution (%)", transform=ax1.transAxes, 
             fontsize=10, fontweight='bold', ha='left', color='#333333')
    ax1.text(-0.05, 0.96, "Inner Ring: Scene Count (N)", transform=ax1.transAxes, 
             fontsize=10, fontweight='bold', ha='left', color='#333333')

    # Title - Using Data Coordinates to fix the gap
    # Radius is 1.0, so -1.2 places it just below the circle regardless of subplot size
    ax1.text(0, -1.2, "(a) Dataset Composition", 
             ha='center', va='top', fontweight='bold', fontsize=12, color='black')

    # ===================================================
    # SUBPLOT 2: Water Distribution (Right Chart)
    # ===================================================
    ax2 = axes[1]
    
    labels_w = list(water_counts.keys())
    values_w = list(water_counts.values())
    
    # Explicitly calculate pctdistance. 
    # Radius=1.0, Width=0.4 => Ring is 0.6 to 1.0. Center is 0.8.
    wedges_w, texts_w, autotexts_w = ax2.pie(
        values_w, 
        labels=None, 
        autopct="%.1f%%", 
        startangle=140, 
        colors=colors_water,
        pctdistance=0.8, # CRITICAL FIX: Position text in the middle of the colored ring
        wedgeprops=dict(width=0.4, edgecolor='white', linewidth=2)
    )
    
    # Force text color and weight
    for autotext in autotexts_w:
        autotext.set_color('white')
        autotext.set_fontweight('bold')
        autotext.set_fontsize(11)

    # Legend inside the donut
    ax2.legend(wedges_w, labels_w, title="Pixel Class",
               loc="center", bbox_to_anchor=(0.5, 0.5),
               fontsize=10, frameon=False)
               
    # Title - Close to chart
    ax2.text(0, -1.2, "(b) Global Pixel Class Balance", 
             ha='center', va='top', fontweight='bold', fontsize=12, color='black')

    # ===================================================
    # Saving
    # ===================================================
    # Remove default titles if any were set by layout managers
    ax1.set_title("")
    ax2.set_title("")
    
    plt.tight_layout()
    # Add a small padding at bottom for the manually placed titles
    plt.subplots_adjust(bottom=0.15) 
    
    save_path = os.path.join(CONFIG["OUTPUT_DIR"], "Fig1_Combined_Stats_V2.pdf")
    plt.savefig(save_path, dpi=CONFIG["DPI"], bbox_inches='tight')
    plt.savefig(save_path.replace(".pdf", ".png"), dpi=CONFIG["DPI"], bbox_inches='tight')
    print(f"[Saved] {save_path}")
    plt.close()

def plot_water_distribution(ratios):
    # [Same as previous Histogram Code]
    ratios_pct = [r * 100 for r in ratios]
    plt.figure(figsize=(8, 5))
    try:
        sns.histplot(ratios_pct, kde=True, bins=20, color='#4c72b0', alpha=0.7)
    except:
        plt.hist(ratios_pct, bins=20, color='#4c72b0', alpha=0.7)
    plt.xlabel("Water Coverage Ratio (%)", fontweight='bold')
    plt.ylabel("Number of Scenes", fontweight='bold')
    plt.gca().xaxis.set_major_formatter(mtick.PercentFormatter(xmax=100))
    plt.gca().spines['top'].set_visible(False)
    plt.gca().spines['right'].set_visible(False)
    plt.grid(axis='y', linestyle='--', alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(CONFIG["OUTPUT_DIR"], "Fig3_Water_Hist.png"), dpi=CONFIG["DPI"])
    plt.close()

def plot_samples():
    """Fig 2: Visual Samples with CORRECT RGB mapping."""
    num_samples = len(CONFIG["SAMPLE_SCENES"])
    fig = plt.figure(figsize=(8, 4 * num_samples))
    gs = gridspec.GridSpec(num_samples, 2, width_ratios=[1, 1], wspace=0.05, hspace=0.2)

    for i, scene_name in enumerate(CONFIG["SAMPLE_SCENES"]):
        truth_name = scene_name.replace(".tif", "_truth.tif")
        
        # 1. Detect Satellite Type first
        sat_type = detect_satellite(scene_name)
        
        # 2. Pass type to reader to get correct bands
        img = read_multiband_image(os.path.join(CONFIG["SCENE_DIR"], scene_name), sat_type)
        lbl = read_label(os.path.join(CONFIG["TRUTH_DIR"], truth_name))

        if img is None or lbl is None: continue

        # Plot RGB
        ax1 = plt.subplot(gs[i, 0])
        ax1.imshow(img)
        ax1.axis("off")
        ax1.text(0.02, 0.98, f"Sample {i+1} ({sat_type})", transform=ax1.transAxes,
                 color='white', fontweight='bold', va='top', bbox=dict(facecolor='black', alpha=0.5))

        # Plot Label
        ax2 = plt.subplot(gs[i, 1])
        ax2.imshow(lbl, cmap="Blues", interpolation='nearest')
        ax2.axis("off")
        ax2.text(0.02, 0.98, "Ground Truth", transform=ax2.transAxes,
                 color='black', fontweight='bold', va='top', bbox=dict(facecolor='white', alpha=0.7))

    save_path = os.path.join(CONFIG["OUTPUT_DIR"], "Fig2_Samples.png")
    # Also save PDF for paper
    plt.savefig(save_path.replace(".png", ".pdf"), dpi=CONFIG["DPI"], bbox_inches='tight')
    plt.savefig(save_path, dpi=CONFIG["DPI"], bbox_inches='tight')
    print(f"[Saved] {save_path}")
    plt.close()

def setup_plot_style():
    plt.rcParams['font.family'] = CONFIG["FONT_FAMILY"]
    plt.rcParams['font.size'] = CONFIG["FONT_SIZE"]
    os.makedirs(CONFIG["OUTPUT_DIR"], exist_ok=True)

def main():
    setup_plot_style()
    print("Calculating stats...")
    sat_pixels, sat_scenes, water_counts, ratios = calculate_dataset_stats()
    
    if sat_pixels:
        plot_combined_statistics(sat_pixels, sat_scenes, water_counts)
        plot_water_distribution(ratios)
        print("Visualizing samples with True Color RGB...")
        plot_samples() # This now uses the fixed logic

if __name__ == "__main__":
    main()
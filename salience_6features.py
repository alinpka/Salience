import cv2
import numpy as np
import os
import csv
import matplotlib.pyplot as plt

STIMULI_DIR = "/Users/macbookair/Desktop/diss/leftstimuli"
OUTPUT_DIR = "/Users/macbookair/Desktop/diss/data"
os.makedirs(OUTPUT_DIR, exist_ok=True)

stimulus_labels = {
    "X": "1",
    "X": "2",
    "X": "3",
    "X": "4",
    "X": "5",
    "X": "6",
    "X": "7",
    "X": "8"
}

def compute_features(frame, prev_frame=None):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).astype(np.float32)
    frame_float = frame.astype(np.float32)
    b, g, r = cv2.split(frame_float)
    rgb_sum = r + g + b
    blur1 = cv2.GaussianBlur(rgb_sum, (0,0), 2)
    blur2 = cv2.GaussianBlur(rgb_sum, (0,0), 10)
    luminance = np.abs(blur1 - blur2)
    luminance = cv2.normalize(luminance, None, 0, 1, cv2.NORM_MINMAX)
    Y = r + g + b + 1e-6
    r_yrb = r / Y
    b_yrb = b / Y
    rg_contrast = np.abs(cv2.GaussianBlur(r_yrb, (0,0), 2) - cv2.GaussianBlur(r_yrb, (0,0), 10))
    by_contrast = np.abs(cv2.GaussianBlur(b_yrb, (0,0), 2) - cv2.GaussianBlur(b_yrb, (0,0), 10))
    colour = rg_contrast + by_contrast
    colour = cv2.normalize(colour, None, 0, 1, cv2.NORM_MINMAX)
    frame_hls = cv2.cvtColor(frame, cv2.COLOR_BGR2HLS).astype(np.float32)
    saturation = frame_hls[:, :, 2] / 255.0
    saturation = cv2.normalize(saturation, None, 0, 1, cv2.NORM_MINMAX)
    kernel_0 = cv2.getGaborKernel((21,21), 4, np.deg2rad(0), 10, 0.5, 0)
    kernel_90 = cv2.getGaborKernel((21,21), 4, np.deg2rad(90), 10, 0.5, 0)
    kernel_45 = cv2.getGaborKernel((21,21), 4, np.deg2rad(45), 10, 0.5, 0)
    kernel_135 = cv2.getGaborKernel((21,21), 4, np.deg2rad(135), 10, 0.5, 0)
    contrast_0_90 = np.abs(cv2.filter2D(gray, cv2.CV_32F, kernel_0)) - np.abs(cv2.filter2D(gray, cv2.CV_32F, kernel_90))
    contrast_45_135 = np.abs(cv2.filter2D(gray, cv2.CV_32F, kernel_45)) - np.abs(cv2.filter2D(gray, cv2.CV_32F, kernel_135))
    orientation = np.abs(contrast_0_90) + np.abs(contrast_45_135)
    orientation = cv2.normalize(orientation, None, 0, 1, cv2.NORM_MINMAX)
    if prev_frame is not None:
        prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY).astype(np.float32)
        motion = (gray - prev_gray) ** 2
    else:
        motion = np.zeros_like(gray)
    motion = cv2.normalize(motion, None, 0, 1, cv2.NORM_MINMAX)
    blur_large = cv2.GaussianBlur(gray, (0,0), 30)
    intensity = np.abs(gray - blur_large)
    intensity = cv2.normalize(intensity, None, 0, 1, cv2.NORM_MINMAX)
    return luminance, colour, saturation, orientation, motion, intensity
    
feature_names = ["luminance_contrast", "colour_contrast", "colour_saturation", "orientation", "motion", "luminance_intensity"]
results = {f: {"affordance": [], "control": [], "labels": []} for f in feature_names}
    
for filename in sorted(os.listdir(STIMULI_DIR)):
    if filename.endswith(".mp4"):
        video_name = filename.replace(".mp4", "")
        video_path = os.path.join(STIMULI_DIR, filename)
        print(f"Processing {video_name}...")
        cap = cv2.VideoCapture(video_path)
        frame_data = {f: {"left": [], "right": []} for f in feature_names}  
        prev_frame = None
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            lum, col, sat, ori, mot, inte = compute_features(frame, prev_frame)
            mid = lum.shape[1] // 2
            for feat, arr in zip(feature_names, [lum, col, sat, ori, mot, inte]):
                frame_data[feat]["left"].append(np.mean(arr[:, :mid]))
                frame_data[feat]["right"].append(np.mean(arr[:, mid:]))
            prev_frame = frame.copy()
        cap.release()
        label = stimulus_labels.get(video_name, video_name)
        for feat in feature_names:
            results[feat]["affordance"].append(np.mean(frame_data[feat]["left"]))
            results[feat]["control"].append(np.mean(frame_data[feat]["right"]))
            results[feat]["labels"].append(label)
        print(f"Done: {video_name}")

csv_path = os.path.join(OUTPUT_DIR, "salience_features_v3.csv")
with open(csv_path, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(["feature", "stimulus", "affordance", "control"])
    for feat in feature_names:
        for i, label in enumerate(results[feat]["labels"]):
            writer.writerow([feat, label, results[feat]["affordance"][i], results[feat]["control$
print(f"Saved CSV to {csv_path}")
            
for feat in feature_names:
    aff = results[feat]["affordance"]
    con = results[feat]["control"]
    labels = results[feat]["labels"]
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.boxplot([aff, con],
               tick_labels=["Affordance Side", "Control Side"],
               patch_artist=True,
               boxprops=dict(facecolor="lightblue", color="black"),
               medianprops=dict(color="black", linewidth=2))
    for i in range(len(aff)):
        linestyle = '--' if labels[i] in ['1', '2', '3', '4'] else '-'
        ax.plot([1, 2], [aff[i], con[i]],
                color="dimgrey", alpha=0.4, linewidth=1, marker="o", markersize=4,
                linestyle=linestyle)
    value_range = max(max(aff), max(con)) - min(min(aff), min(con))
    gap = value_range * 0.02
    sorted_pairs = sorted(zip(con, labels), key=lambda x: x[0])
    used_positions = []   
    for y_val, label in sorted_pairs:
        y = y_val
        while any(abs(y - pos) < gap for pos in used_positions):
            y += gap
        used_positions.append(y) 
        ax.text(2.12, y, label, fontsize=14, va="center")
    ax.set_xlim(1 - 0.5, 2 + 0.7)
    ax.set_ylabel("Salience", fontsize=18)
    ax.set_title(f"{feat.replace('_', ' ').title()}", fontsize=20)
    ax.tick_params(axis='both', labelsize=16)
    plt.tight_layout()
    plot_path = os.path.join(OUTPUT_DIR, f"salience_{feat}_v3.png")
    plt.savefig(plot_path, dpi=150)
    plt.close()
    print(f"Saved plot: salience_{feat}_v3.png")
               
print("\nAll done!")

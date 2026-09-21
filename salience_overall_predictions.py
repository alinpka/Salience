import cv2
import numpy as np
import os
import csv
import matplotlib.pyplot as plt

STIMULI_DIR = "X"
OUTPUT_DIR = "X"
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

def compute_overall_saliency(frame, prev_frame=None):
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
    contrast_0_90 = np.abs(cv2.filter2D(gray, cv2.CV_32F, kernel_0)) - np.abs(cv2.filter2D(gray,$
    contrast_45_135 = np.abs(cv2.filter2D(gray, cv2.CV_32F, kernel_45)) - np.abs(cv2.filter2D(gr$
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
    
    combined = (luminance + colour + saturation + orientation + motion + intensity) / 6
    
    # Probability normalisation
    combined = np.clip(combined, 0, None)
    total = np.sum(combined)
    if total > 0:
        combined = combined / total
    
    # Noise
    uniform_noise = 0.01 / combined.size
    combined = combined * 0.99 + uniform_noise
    
    return combined
    
results = []
        
for filename in sorted(os.listdir(STIMULI_DIR)):
    if filename.endswith(".mp4"):
        video_name = filename.replace(".mp4", "")
        video_path = os.path.join(STIMULI_DIR, filename)
        print(f"Processing {video_name}...")
        cap = cv2.VideoCapture(video_path)
        left_sums = []
        right_sums = []
        prev_frame = None
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            overall = compute_overall_saliency(frame, prev_frame)
            mid = overall.shape[1] // 2
            left_sums.append(np.sum(overall[:, :mid]))
            right_sums.append(np.sum(overall[:, mid:]))
            prev_frame = frame.copy()
        cap.release()
        avg_left = np.mean(left_sums)
        avg_right = np.mean(right_sums)
        results.append({
            "video": video_name,
            "stimulus_label": stimulus_labels.get(video_name, video_name),
            "affordance_prediction": avg_left,
            "control_prediction": avg_right
        })
        print(f"Done: {video_name} — affordance: {avg_left:.4f}, control: {avg_right:.4f}")
        
csv_path = os.path.join(OUTPUT_DIR, "salience_final_predictions.csv")
with open(csv_path, 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=["video", "stimulus_label", "affordance_prediction", "$
    writer.writeheader()
    writer.writerows(results)
print(f"Saved CSV to {csv_path}")
            
affordance_vals = [r["affordance_prediction"] for r in results]
control_vals = [r["control_prediction"] for r in results]
labels = [r["stimulus_label"] for r in results]
            
fig, ax = plt.subplots(figsize=(8, 6))
ax.boxplot([affordance_vals, control_vals],
           tick_labels=["Affordance Side", "Control Side"],
           patch_artist=True,
           boxprops=dict(facecolor="lightblue", color="black"),
           medianprops=dict(color="black", linewidth=2))
for i in range(len(affordance_vals)):
    linestyle = '--' if labels[i] in ['1', '2', '3', '4'] else '-'
    ax.plot([1, 2], [affordance_vals[i], control_vals[i]],
            color="dimgrey", alpha=0.4, linewidth=1, marker="o", markersize=4,
            linestyle=linestyle)
value_range = max(max(affordance_vals), max(control_vals)) - min(min(affordance_vals), min(contr$
gap = value_range * 0.02
sorted_pairs = sorted(zip(control_vals, labels), key=lambda x: x[0])
used_positions = []
for y_val, label in sorted_pairs:
    y = y_val
    while any(abs(y - pos) < gap for pos in used_positions):
        y += gap
    used_positions.append(y)
    ax.text(2.12, y, label, fontsize=14, va="center")
ax.set_xlim(1 - 0.5, 2 + 0.7)
ax.set_ylabel("Looking probability", fontsize=18)
ax.set_title("Looking predictions based on visual salience", fontsize=20)
ax.tick_params(axis='both', labelsize=16)
plt.tight_layout()
plot_path = os.path.join(OUTPUT_DIR, "salience_overall_predictions.png")
plt.savefig(plot_path, dpi=150)
plt.close()
print(f"Saved plot to {plot_path}")
print("All done!")

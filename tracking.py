import os
import re
import cv2
import math
import numpy as np
import pandas as pd


#######################
# 1) Utility Functions
#######################

def detect_bright_spots(gray, threshold_value=200, min_area=2, max_area=300):
    """
    Detect bright spots in a grayscale image using threshold + contours.
    Returns a list of (x, y) centers for each bright spot.
    """
    _, thresh = cv2.threshold(gray, threshold_value, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    spots = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < min_area or area > max_area:
            continue
        M = cv2.moments(cnt)
        if M["m00"] != 0:
            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])
            spots.append((cx, cy))
    return spots


def match_spots(ref_spots, new_spots, max_dist=20):
    """
    Nearest-neighbor matching from ref_spots to new_spots.
    Returns a list of pairs (i_ref, i_new).
    """
    matches = []
    used_new = set()

    for i_ref, (rx, ry) in enumerate(ref_spots):
        best_j = None
        best_d = float('inf')
        for j_new, (nx, ny) in enumerate(new_spots):
            if j_new in used_new:
                continue
            d = math.hypot(nx - rx, ny - ry)
            if d < best_d and d <= max_dist:
                best_d = d
                best_j = j_new

        if best_j is not None:
            matches.append((i_ref, best_j))
            used_new.add(best_j)

    return matches


def draw_matches(base_frame, ref_spots, new_spots, matches):
    """
    Draw lines between matching spots, and circles on each matched spot in new_spots.
    Returns an annotated copy of base_frame.
    """
    annotated = base_frame.copy()
    for (i_ref, i_new) in matches:
        (rx, ry) = ref_spots[i_ref]
        (nx, ny) = new_spots[i_new]
        # Circle on the new spot
        cv2.circle(annotated, (nx, ny), 6, (0, 255, 0), 2)
        # Draw line from reference position to the new position (for illustration)
        # Because we only have the new image, we might just show the new positions.
        # Alternatively, you can do arrowedLine from (nx, ny) to (nx + dx, ny + dy) if needed.
        # We'll skip lines or do something simple:
        # cv2.arrowedLine(annotated, (nx, ny), (nx + (rx-nx), ny + (ry-ny)), (255,0,0), 2)
    return annotated


#######################
# 2) Main Script
#######################
def main():
    # Path to your tilt_calibration folder
    pan_folder = "saved/pan_calibration"  # adjust if needed
    tracked_folder = os.path.join(pan_folder, "tracked")
    os.makedirs(tracked_folder, exist_ok=True)

    # We read config.yaml just to confirm zero pan/tilt (optional).
    # If you need them, parse them here. For demonstration:
    zero_pan = 0.0
    zero_tilt = 3.2

    # Find all .jpg images in tilt_calibration
    all_files = [f for f in os.listdir(pan_folder) if f.lower().endswith(".jpg")]
    all_files.sort()  # sort by filename

    # OPTIONAL: Identify the "zero tilt" image. Suppose it has "tilt_enc_3.20_pan_0.00_" in the name.
    # Or if you know the exact file name, you can do it directly.
    # We'll do a quick regex search:
    reference_file = None
    ref_pattern = re.compile(r"pan_enc_?(-?\d+\.\d+)_tilt_?(-?\d+\.\d+)_")
    best_diff = 99999
    for f in all_files:
        match = ref_pattern.search(f)
        if match:
            tilt_val = float(match.group(1))
            pan_val = float(match.group(2))
            # measure how close to (zero_pan, zero_tilt)
            diff = abs(pan_val - zero_pan) + abs(tilt_val - zero_tilt)
            if diff < best_diff:
                best_diff = diff
                reference_file = f

    if reference_file is None:
        print("ERROR: Could not find a zero tilt reference image in folder.")
        return
    print("Reference file (closest to zero pan/tilt) is:", reference_file)

    # Load the reference image
    ref_path = os.path.join(pan_folder, reference_file)
    ref_img = cv2.imread(ref_path)
    if ref_img is None:
        print(f"Failed to read {reference_file}")
        return
    ref_gray = cv2.cvtColor(ref_img, cv2.COLOR_BGR2GRAY)
    ref_spots = detect_bright_spots(ref_gray, threshold_value=200)  # tweak as needed
    print(f"Detected {len(ref_spots)} bright spots in reference image.")

    # We'll track up to 10 frames for demonstration
    # Exclude the reference file from processing
    image_files = [f for f in all_files if f != reference_file]
    # image_files = image_files[:10]  # take first 10

    # We'll store results in a DataFrame
    columns = ["filename", "pan", "tilt", "avg_dx", "avg_dy"]
    results = []

    # Regex for extracting "tilt" and "pan" from the filename
    # e.g. tilt_enc_3.20_pan_0.00_offset_....jpg
    pattern = re.compile(r"tilt_enc_?(-?\d+\.\d+)_pan_?(-?\d+\.\d+)_")

    for fname in image_files:
        filepath = os.path.join(pan_folder, fname)
        print(f"Processing: {fname}")
        m = pattern.search(fname)
        if not m:
            print("  Could not parse pan/tilt from filename. Skipping.")
            continue
        tilt_val = float(m.group(1))
        pan_val = float(m.group(2))

        # Load the image
        img = cv2.imread(filepath)
        if img is None:
            print(f"  Failed to read {fname}, skipping.")
            continue

        # Detect bright spots
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        new_spots = detect_bright_spots(gray, threshold_value=100)

        # Match to reference
        matches = match_spots(ref_spots, new_spots, max_dist=300)
        print(f"  Found {len(new_spots)} new spots, matched {len(matches)} with reference.")

        # Compute average dx, dy over matched pairs
        dx_vals = []
        dy_vals = []
        for (i_ref, i_new) in matches:
            rx, ry = ref_spots[i_ref]
            nx, ny = new_spots[i_new]
            dx_vals.append(nx - rx)
            dy_vals.append(ny - ry)
        if len(matches) > 0:
            avg_dx = sum(dx_vals) / len(dx_vals)
            avg_dy = sum(dy_vals) / len(dy_vals)
        else:
            avg_dx = 0
            avg_dy = 0

        # Draw annotations
        annotated = draw_matches(img, ref_spots, new_spots, matches)

        # Save annotated image in "tracked" folder
        out_name = os.path.splitext(fname)[0] + "_tracked.jpg"
        out_path = os.path.join(tracked_folder, out_name)
        # cv2.imwrite(out_path, annotated)

        # Record results
        row = {
            "filename": fname,
            "pan": pan_val,
            "tilt": tilt_val,
            "avg_dx": avg_dx,
            "avg_dy": avg_dy
        }
        results.append(row)

    # Create a DataFrame
    df = pd.DataFrame(results, columns=columns)
    print("\n=== Results DataFrame ===")
    print(df)

    # (Optionally) Save it as CSV
    csv_path = os.path.join(tracked_folder, "tilt_tracking_results.csv")
    df.to_csv(csv_path, index=False)
    print(f"Saved results to {csv_path}")


if __name__ == "__main__":
    main()

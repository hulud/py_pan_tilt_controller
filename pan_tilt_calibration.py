#!/usr/bin/env python3
import os
import cv2
import time
import numpy as np
from pelco_D_api import PelcoDController


def clear_directory(directory):
    if os.path.exists(directory):
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.remove(file_path)
                elif os.path.isdir(file_path):
                    os.rmdir(file_path)
            except Exception as e:
                print(f"Failed to delete {file_path}. Reason: {e}")
    else:
        os.makedirs(directory)


def sharpen_image(gray):
    """Apply a simple sharpening filter to the grayscale image."""
    kernel = np.array([[0, -1, 0],
                       [-1, 5, -1],
                       [0, -1, 0]])
    return cv2.filter2D(gray, -1, kernel)


def select_edge_point(gray, center, search_radius=50):
    """
    Detect edges using Canny and select an edge point near the center.
    If no edges are found within the search radius, fallback to the center.
    """
    edges = cv2.Canny(gray, 50, 150)
    edge_points = cv2.findNonZero(edges)
    if edge_points is None:
        return np.array([[[center[0], center[1]]]], dtype=np.float32)
    edge_points = edge_points.squeeze()  # shape: (N, 2)
    distances = np.linalg.norm(edge_points - np.array(center), axis=1)
    candidate_idx = np.where(distances < search_radius)[0]
    if candidate_idx.size > 0:
        best_idx = candidate_idx[np.argmin(distances[candidate_idx])]
    else:
        best_idx = np.argmin(distances)
    best_point = edge_points[best_idx]
    return np.array([[[float(best_point[0]), float(best_point[1])]]], dtype=np.float32)


def main():
    # Directories for saving images
    pan_calib_dir = "pan_calibration"
    tilt_calib_dir = "tilt_calibration"
    clear_directory(pan_calib_dir)
    clear_directory(tilt_calib_dir)
    print(f"Cleared directories '{pan_calib_dir}' and '{tilt_calib_dir}'.")

    # Open the camera (adjust the index if needed)
    cap = cv2.VideoCapture(1)
    # Request full resolution (2592 x 2048)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 2592)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 2048)

    # Verify camera resolution
    width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    print(f"Camera resolution set to: {width} x {height}")
    if not cap.isOpened():
        print("Error: Could not open the camera.")
        return

    # Initialize the Pelco-D controller with blocking enabled.
    try:
        controller = PelcoDController(port='COM3', baudrate=9600, address=1, blocking=True)
    except Exception as e:
        print("Error initializing PelcoDController:", e)
        cap.release()
        return

    # --- Set Zero Position ---
    # New zero position: pan = 0°, tilt = 6.85°
    print("Setting zero position: pan = 0°, tilt = 6.85°")
    controller.absolute_pan(0)      # Blocks until reached.
    controller.absolute_tilt(6.85)    # Blocks until reached.
    print("Zero position reached.")
    time.sleep(0.5)  # Short pause

    # --- Capture Baseline Frame ---
    # At zero position the tracking object is assumed to be at the center.
    ret, baseline_frame = cap.read()
    if not ret:
        print("Error: Failed to capture baseline frame.")
        cap.release()
        controller.close()
        return

    # Convert to grayscale and enhance edges.
    baseline_gray = cv2.cvtColor(baseline_frame, cv2.COLOR_BGR2GRAY)
    baseline_gray = sharpen_image(baseline_gray)
    h, w = baseline_gray.shape
    center = (w / 2, h / 2)
    # Choose a baseline point on a strong edge near the center.
    baseline_point = select_edge_point(baseline_gray, center)
    print(f"Baseline tracking point (from edge selection): {baseline_point[0, 0]}")

    # --- Optical Flow Parameters for Tracking ---
    # Use a smaller window and tighter criteria for better edge sensitivity.
    lk_params = dict(winSize=(9, 9),
                     maxLevel=3,
                     criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 15, 0.01))

    # -------- Pan Sweep --------
    # Sweep from (0 - 5)° to (0 + 5)° in 0.3° increments.
    pan_start = 0 - 5
    pan_end = 0 + 5
    print(f"\nStarting pan sweep from {pan_start:.2f}° to {pan_end:.2f}° in 0.3° increments")

    # For pan sweep, assume tilt remains fixed at 6.85°
    # Initialize optical flow reference with the baseline frame & chosen point.
    prev_gray = baseline_gray.copy()
    prev_point = baseline_point.copy()

    for cmd_pan in np.arange(pan_start, pan_end + 0.001, 0.3):
        print(f"\nCommanding pan to {cmd_pan:.2f}° ...")
        controller.absolute_pan(cmd_pan)  # Blocks until reached.
        measured_pan = cmd_pan
        measured_tilt = 6.85  # Fixed for pan sweep

        # Capture frame after the move.
        ret, frame = cap.read()
        if not ret:
            print("Warning: Failed to capture an image for this pan value. Skipping.")
            continue

        current_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        current_gray = sharpen_image(current_gray)
        # Compute optical flow from previous frame to current frame.
        new_point, status, err = cv2.calcOpticalFlowPyrLK(prev_gray, current_gray, prev_point, None, **lk_params)
        if new_point is not None and status is not None and status[0][0] == 1:
            tracked_point = new_point
        else:
            print("Optical flow tracking failed; using previous point.")
            tracked_point = prev_point

        # Extract coordinates.
        x, y = map(int, tracked_point[0, 0])
        # Draw a circle around the tracked point.
        cv2.circle(frame, (x, y), radius=10, color=(0, 255, 0), thickness=2)
        # Compute offset relative to the baseline center.
        dx = x - int(w / 2)
        dy = y - int(h / 2)
        print(f"Pan sweep: tracked point at pixel ({x}, {y}), offset from center: ({dx}, {dy})")

        # Save the image with the commanded values and offset in the filename.
        filename = f"pan_enc_{measured_pan:.2f}_tilt_{measured_tilt:.2f}_offset_{dx}_{dy}_cmd_{cmd_pan:.2f}.jpg"
        filepath = os.path.join(pan_calib_dir, filename)
        if cv2.imwrite(filepath, frame, [cv2.IMWRITE_JPEG_QUALITY, 95]):
            print(f"Saved pan image: {filepath}")
        else:
            print(f"Error: Could not save pan image to {filepath}")

        # Update optical flow references for the next iteration.
        prev_gray = current_gray.copy()
        prev_point = tracked_point

    # -------- Tilt Sweep --------
    # Sweep from (6.85 - 5)° to (6.85 + 5)° in 0.3° increments.
    tilt_start = 6.85 - 5
    tilt_end = 6.85 + 5
    print(f"\nStarting tilt sweep from {tilt_start:.2f}° to {tilt_end:.2f}° in 0.3° increments")

    # For tilt sweep, assume pan remains fixed at 0°.
    # Reinitialize optical flow reference using the baseline frame.
    prev_gray = baseline_gray.copy()
    prev_point = baseline_point.copy()

    for cmd_tilt in np.arange(tilt_start, tilt_end + 0.001, 0.3):
        print(f"\nCommanding tilt to {cmd_tilt:.2f}° ...")
        controller.absolute_tilt(cmd_tilt)  # Blocks until reached.
        measured_tilt = cmd_tilt
        measured_pan = 0.0  # Fixed for tilt sweep

        # Capture frame after the move.
        ret, frame = cap.read()
        if not ret:
            print("Warning: Failed to capture an image for this tilt value. Skipping.")
            continue

        current_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        current_gray = sharpen_image(current_gray)
        # Compute optical flow from previous frame to current frame.
        new_point, status, err = cv2.calcOpticalFlowPyrLK(prev_gray, current_gray, prev_point, None, **lk_params)
        if new_point is not None and status is not None and status[0][0] == 1:
            tracked_point = new_point
        else:
            print("Optical flow tracking failed; using previous point.")
            tracked_point = prev_point

        # Extract coordinates.
        x, y = map(int, tracked_point[0, 0])
        # Draw a circle around the tracked point.
        cv2.circle(frame, (x, y), radius=10, color=(0, 255, 0), thickness=2)
        # Compute offset relative to the baseline center.
        dx = x - int(w / 2)
        dy = y - int(h / 2)
        print(f"Tilt sweep: tracked point at pixel ({x}, {y}), offset from center: ({dx}, {dy})")

        # Save the image with the commanded values and offset in the filename.
        filename = f"tilt_enc_{measured_tilt:.2f}_pan_{measured_pan:.2f}_offset_{dx}_{dy}_cmd_{cmd_tilt:.2f}.jpg"
        filepath = os.path.join(tilt_calib_dir, filename)
        if cv2.imwrite(filepath, frame, [cv2.IMWRITE_JPEG_QUALITY, 95]):
            print(f"Saved tilt image: {filepath}")
        else:
            print(f"Error: Could not save tilt image to {filepath}")

        # Update optical flow references.
        prev_gray = current_gray.copy()
        prev_point = tracked_point

    # --- Return to Zero Position ---
    print("\nReturning to zero position...")
    controller.absolute_pan(0)      # Blocks until reached.
    controller.absolute_tilt(6.85)    # Blocks until reached.
    print("Returned to zero position.")

    # Cleanup
    cap.release()
    controller.close()
    print("\nCalibration complete.")


if __name__ == '__main__':
    main()

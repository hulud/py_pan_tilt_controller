#!/usr/bin/env python3
import os
import cv2
import time
import numpy as np
import yaml
from pelco_D_api import PelcoDController
from tracking import (sharpen_image, select_edge_point, select_bright_dot,
                      track_point, draw_tracked_point)


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


def get_filtered_frame(cap):
    """
    Reads a frame from the camera, flips it vertically,
    converts it to grayscale, applies a Gaussian filter for noise reduction,
    and then applies a sharpening filter.
    Returns a tuple (original_frame, filtered_gray).
    """
    ret, frame = cap.read()
    if not ret:
        return None, None
    # Flip vertically to correct vertical mirror image
    frame = cv2.flip(frame, 0)
    # Convert to grayscale
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    # Apply Gaussian blur (kernel size 5x5, sigma 0)
    gaussian = cv2.GaussianBlur(gray, (15, 15), 0)
    # Apply sharpening filter on the blurred image
    # filtered = sharpen_image(gaussian)
    return frame, gaussian


def main():
    # --- Load configuration from YAML ---
    with open("config.yaml", "r") as f:
        config = yaml.safe_load(f)

    # Communication parameters
    comm = config["communication"]
    port = comm["port"]
    baudrate = comm["baudrate"]
    address = comm["address"]
    blocking = comm["blocking"]

    # Camera parameters
    cam_index = config["camera"]["index"]
    cam_width = config["camera"]["width"]
    cam_height = config["camera"]["height"]

    # Zero positions
    zero_pan = config["zero"]["pan"]
    zero_tilt = config["zero"]["tilt"]

    # Sweep parameters (the sweep range is relative to the zero position)
    pan_range = config["sweep"]["pan_range"]
    tilt_range = config["sweep"]["tilt_range"]
    sweep_step = config["sweep"]["step"]

    # Compute continuous sweep positions.
    # For each axis, we create positions relative to zero:
    # First, ascending from 0 to +range; then descending from +range to -range.
    pan_vals = np.concatenate([
        np.arange(0, pan_range + sweep_step, sweep_step),
        np.arange(pan_range, -pan_range - sweep_step, -sweep_step)
    ])
    pan_positions = zero_pan + pan_vals

    tilt_vals = np.concatenate([
        np.arange(0, tilt_range + sweep_step, sweep_step),
        np.arange(tilt_range, -tilt_range - sweep_step, -sweep_step)
    ])
    tilt_positions = zero_tilt + tilt_vals

    # Tracking options
    tracking_mode = config["tracking"]["mode"]  # "bright" or "edge"
    edge_search_radius = config["tracking"]["edge_search_radius"]
    bright_threshold = config["tracking"]["bright_threshold"]
    bright_search_radius = config["tracking"]["bright_search_radius"]

    # Optical flow (LK) parameters
    lk_params = dict(
        winSize=tuple(config["lk_params"]["win_size"]),
        maxLevel=config["lk_params"]["max_level"],
        criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT,
                  config["lk_params"]["term_crit_count"],
                  config["lk_params"]["term_crit_eps"])
    )

    # Directories for saving images
    pan_calib_dir = "pan_calibration"
    tilt_calib_dir = "tilt_calibration"
    clear_directory(pan_calib_dir)
    clear_directory(tilt_calib_dir)
    print(f"Cleared directories '{pan_calib_dir}' and '{tilt_calib_dir}'.")

    # Open the camera
    cap = cv2.VideoCapture(cam_index)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, cam_width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cam_height)
    width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    print(f"Camera resolution set to: {width} x {height}")
    if not cap.isOpened():
        print("Error: Could not open the camera.")
        return

    # Initialize the Pelco-D controller
    try:
        controller = PelcoDController(port=port, baudrate=baudrate, address=address, blocking=blocking)
    except Exception as e:
        print("Error initializing PelcoDController:", e)
        cap.release()
        return

    # --- Set Zero Position ---
    print(f"Setting zero position: pan = {zero_pan}°, tilt = {zero_tilt}°")
    controller.absolute_pan(zero_pan)
    controller.absolute_tilt(zero_tilt)
    print("Zero position reached.")
    time.sleep(0.5)

    # --- Capture Baseline Frame ---
    frame, baseline_gray = get_filtered_frame(cap)
    if frame is None or baseline_gray is None:
        print("Error: Failed to capture baseline frame.")
        cap.release()
        controller.close()
        return
    h_img, w_img = baseline_gray.shape
    center = (w_img / 2, h_img / 2)

    # Select baseline tracking point according to the mode.
    if tracking_mode == 'bright':
        baseline_point = select_bright_dot(baseline_gray, center, bright_threshold, bright_search_radius)
        print(f"Using bright dot tracking mode. Baseline tracking point: {baseline_point[0, 0]}")
    else:
        baseline_point = select_edge_point(baseline_gray, center, edge_search_radius)
        print(f"Using edge tracking mode. Baseline tracking point: {baseline_point[0, 0]}")

    # ------------- PAN SWEEP -------------
    print(f"\nStarting continuous pan sweep from {pan_positions[0]:.2f}° to {pan_positions[-1]:.2f}°")
    prev_gray = baseline_gray.copy()
    prev_point = baseline_point.copy()

    for cmd_pan in pan_positions:
        print(f"\nCommanding pan to {cmd_pan:.2f}° ...")
        controller.absolute_pan(cmd_pan)
        measured_pan = cmd_pan
        measured_tilt = zero_tilt  # pan sweep holds tilt constant

        frame, current_gray = get_filtered_frame(cap)
        if frame is None or current_gray is None:
            print("Warning: Failed to capture frame for pan sweep. Skipping.")
            continue

        if tracking_mode == 'bright':
            tracked_point = select_bright_dot(current_gray, center, bright_threshold, bright_search_radius)
        else:
            tracked_point = track_point(prev_gray, current_gray, prev_point, lk_params)

        frame = draw_tracked_point(frame, tracked_point, radius=10, color=(0, 255, 0), thickness=2)
        x, y = map(int, tracked_point[0, 0])
        dx = x - int(w_img / 2)
        dy = y - int(h_img / 2)
        print(f"Pan sweep: tracked point at ({x}, {y}), offset: ({dx}, {dy})")

        filename = f"pan_enc_{measured_pan:.2f}_tilt_{measured_tilt:.2f}_offset_{dx}_{dy}_cmd_{cmd_pan:.2f}.jpg"
        filepath = os.path.join(pan_calib_dir, filename)
        if cv2.imwrite(filepath, frame, [cv2.IMWRITE_JPEG_QUALITY, 95]):
            print(f"Saved pan image: {filepath}")
        else:
            print(f"Error: Could not save pan image to {filepath}")

        prev_gray = current_gray.copy()
        prev_point = tracked_point

    # --- Go back to zero before starting tilt scan ---
    print("\nReturning to zero position between pan and tilt scans...")
    controller.absolute_pan(zero_pan)
    controller.absolute_tilt(zero_tilt)
    time.sleep(0.5)

    # ------------- TILT SWEEP -------------
    print(f"\nStarting continuous tilt sweep from {tilt_positions[0]:.2f}° to {tilt_positions[-1]:.2f}°")
    prev_gray = baseline_gray.copy()
    prev_point = baseline_point.copy()

    for cmd_tilt in tilt_positions:
        print(f"\nCommanding tilt to {cmd_tilt:.2f}° ...")
        controller.absolute_tilt(cmd_tilt)
        measured_tilt = cmd_tilt
        measured_pan = 0.0  # tilt sweep holds pan constant

        frame, current_gray = get_filtered_frame(cap)
        if frame is None or current_gray is None:
            print("Warning: Failed to capture frame for tilt sweep. Skipping.")
            continue

        if tracking_mode == 'bright':
            tracked_point = select_bright_dot(current_gray, center, bright_threshold, bright_search_radius)
        else:
            tracked_point = track_point(prev_gray, current_gray, prev_point, lk_params)

        frame = draw_tracked_point(frame, tracked_point, radius=10, color=(0, 255, 0), thickness=2)
        x, y = map(int, tracked_point[0, 0])
        dx = x - int(w_img / 2)
        dy = y - int(h_img / 2)
        print(f"Tilt sweep: tracked point at ({x}, {y}), offset: ({dx}, {dy})")

        filename = f"tilt_enc_{measured_tilt:.2f}_pan_{measured_pan:.2f}_offset_{dx}_{dy}_cmd_{cmd_tilt:.2f}.jpg"
        filepath = os.path.join(tilt_calib_dir, filename)
        if cv2.imwrite(filepath, frame, [cv2.IMWRITE_JPEG_QUALITY, 95]):
            print(f"Saved tilt image: {filepath}")
        else:
            print(f"Error: Could not save tilt image to {filepath}")

        prev_gray = current_gray.copy()
        prev_point = tracked_point

    # --- Return to Zero Position at the End ---
    print("\nReturning to zero position at the end of scans...")
    controller.absolute_pan(zero_pan)
    controller.absolute_tilt(zero_tilt)
    print("Returned to zero position.")

    cap.release()
    controller.close()
    print("\nCalibration complete.")


if __name__ == '__main__':
    main()

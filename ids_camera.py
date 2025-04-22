import cv2

cap = cv2.VideoCapture(0)  # Open the camera (make sure the index is correct)


cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)   # set width to 1920 pixels
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)  # set height to 1080 pixels


# Verify the settings (note: not all drivers honor these settings)
width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
print(f"Camera resolution set to: {width} x {height}")

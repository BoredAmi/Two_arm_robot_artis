"""
Robot Camera Capture (local) for Robot Drawing System.

This module replaces FTP-based image retrieval with a simple local camera
capture utility. It uses OpenCV to capture a single frame from a connected
camera (USB/webcam) and saves it to disk. The import attempts to avoid
requiring OpenCV at import-time; cv2 is imported lazily in the capture method
so the rest of the project can import this module even if OpenCV isn't
installed in the environment.

Usage:
    python robot_ftp_downloader.py    # captures one frame and saves to DEFAULT_LOCAL_PATH

Notes:
    - Defaults to camera index 0. If you have multiple cameras, set camera_index.
    - If OpenCV is missing, the capture method will raise an ImportError with a
      clear message instructing how to install it: `pip install opencv-python`.
"""

import os
import sys
import time


class RobotCameraCapture:
    """Capture a single frame from a local camera and save to disk."""

    DEFAULT_LOCAL_PATH = "image.png"

    def __init__(self, camera_index=0, local_path=None):
        self.camera_index = int(camera_index)
        self.local_path = local_path or self.DEFAULT_LOCAL_PATH

    def capture_image(self, camera_index=None, local_path=None, timeout=1.0, *, fast=False, resolution=(640, 480), attempts=3):
        """
        Capture a single image from the local camera and save it.

        Args:
            camera_index (int): OS camera index (default uses instance or 0)
            local_path (str): Local file path to save the captured image
            timeout (float): Maximum seconds to spend trying to capture (total)
            fast (bool): If True, use faster capture strategy (lower res, shorter warm-up)
            resolution (tuple): (width, height) to request when fast=True
            attempts (int): Number of short-read attempts before giving up

        Returns:
            bool: True on success, False on failure
        """
        cam_idx = int(camera_index) if camera_index is not None else self.camera_index
        out_path = local_path or self.local_path

        try:
            import cv2
        except Exception:
            raise ImportError("OpenCV (cv2) is required for local camera capture. Install with: pip install opencv-python")

        # Prefer DirectShow on Windows for faster startup when available
        backend = cv2.CAP_DSHOW if hasattr(cv2, 'CAP_DSHOW') else 0
        try:
            cap = cv2.VideoCapture(cam_idx, backend)
        except Exception:
            cap = cv2.VideoCapture(cam_idx)

        if not cap.isOpened():
            print(f"Failed to open camera index {cam_idx}")
            return False

        # Fast mode: request lower resolution and reduce warm-up
        if fast:
            try:
                w, h = int(resolution[0]), int(resolution[1])
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, w)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, h)
                # some backends support buffer size - attempt but ignore failures
                try:
                    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                except Exception:
                    pass
            except Exception:
                pass

        # Try a small number of short reads instead of long warm-up loop
        frame = None
        start = time.time()
        delay = max(0.02, float(timeout) / max(1, attempts))
        for i in range(max(1, attempts)):
            ret = False
            try:
                # grab+retrieve can be slightly faster on some backends
                if hasattr(cap, 'grab'):
                    if cap.grab():
                        ret, frame = cap.retrieve()
                else:
                    ret, frame = cap.read()
            except Exception:
                ret = False

            if ret and frame is not None:
                break

            # brief pause but don't exceed overall timeout
            if time.time() - start >= float(timeout):
                break
            time.sleep(delay)

        cap.release()

        if frame is None:
            print("No frame captured from camera")
            return False

        # Write image
        try:
            d = os.path.dirname(os.path.abspath(out_path))
            if d and not os.path.exists(d):
                os.makedirs(d, exist_ok=True)
            success = cv2.imwrite(out_path, frame)
            if not success:
                print(f"Failed to write image to {out_path}")
                return False
        except Exception as e:
            print(f"Error saving image: {e}")
            return False

        print(f"Captured camera {cam_idx} -> {out_path}")
        return True


def main():
    # Simple CLI entry: capture one frame and save
    cam = RobotCameraCapture()
    ok = cam.capture_image()
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
import serial
import time
import threading


class PelcoDController:
    def __init__(self, port='COM3', baudrate=9600, address=1, blocking=False, timeout=1.0):
        """
        Initialize the Pelco D controller.

        - Opens the serial port.
        - Immediately queries the device version for verification.

        Parameters:
          port      : Serial port to use.
          baudrate  : Baud rate.
          address   : Device address.
          blocking  : If True, movement commands will block until the encoder reports
                      that the target position is reached (default: False).
          timeout   : Serial port timeout.
        """
        try:
            self.ser = serial.Serial(
                port=port,
                baudrate=baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=timeout
            )
            print(f"Connected to {port} at {baudrate} baud.")
        except Exception as e:
            print("Error opening serial port:", e)
            self.ser = None
            raise e

        self.address = address
        self.blocking = blocking
        self.rt_feedback_active = False
        self.feedback_thread = None
        self.rt_callback = self._default_rt_callback

        version = self.query_version()
        if version is None:
            print("Error: Failed to retrieve device version. Closing connection.")
            self.close()
            raise Exception("Failed to retrieve device version.")
        else:
            print("Device version:", version)

    def _default_rt_callback(self, data):
        print("Real-time feedback:", data)

    def send_command(self, command):
        self.ser.write(command)
        print("Sent:", " ".join(f"{b:02X}" for b in command))

    def create_command(self, cmd1, cmd2, data1, data2):
        checksum = (self.address + cmd1 + cmd2 + data1 + data2) & 0xFF
        return bytearray([0xFF, self.address, cmd1, cmd2, data1, data2, checksum])

    def _read_response(self, expected_length, timeout=1.0):
        start = time.time()
        data = bytearray()
        while time.time() - start < timeout:
            if self.ser.in_waiting:
                data.extend(self.ser.read(self.ser.in_waiting))
            if len(data) >= expected_length:
                break
            time.sleep(0.05)
        return data

    # =============================
    #      Version & Query
    # =============================
    def query_version(self):
        cmd = self.create_command(0xD2, 0x01, 0x00, 0x00)
        self.send_command(cmd)
        time.sleep(0.2)
        response = bytearray()
        start = time.time()
        while time.time() - start < 1.0:
            if self.ser.in_waiting:
                response.extend(self.ser.read(self.ser.in_waiting))
                if response:
                    break
            time.sleep(0.1)
        if response:
            try:
                return response.decode('ascii', errors='replace')
            except Exception:
                return response.hex()
        else:
            return None

    def query_pan_position(self):
        cmd = bytearray([0xFF, self.address, 0x00, 0x51, 0x00, 0x00])
        checksum = (self.address + 0x00 + 0x51 + 0x00 + 0x00) & 0xFF
        cmd.append(checksum)
        self.send_command(cmd)
        time.sleep(0.2)
        response = self._read_response(expected_length=4, timeout=1.0)
        if len(response) == 4:
            if response[0] != 0x59:
                print("Pan query: Unexpected command indicator:", hex(response[0]))
                return None
            p_data = (response[1] << 8) | response[2]
            return p_data / 100.0
        elif len(response) >= 5:
            if response[1] != 0x59:
                print("Pan query: Unexpected command indicator:", hex(response[1]))
                return None
            p_data = (response[2] << 8) | response[3]
            return p_data / 100.0
        else:
            print("Pan query: Incomplete response:", response.hex())
            return None

    def query_tilt_position(self):
        cmd = bytearray([0xFF, self.address, 0x00, 0x53, 0x00, 0x00])
        checksum = (self.address + 0x00 + 0x53 + 0x00 + 0x00) & 0xFF
        cmd.append(checksum)
        self.send_command(cmd)
        time.sleep(0.2)
        response = self._read_response(expected_length=4, timeout=1.0)
        if len(response) == 4:
            if response[0] != 0x5B:
                print("Tilt query: Unexpected command indicator:", hex(response[0]))
                return None
            t_data = (response[1] << 8) | response[2]
        elif len(response) >= 5:
            if response[1] != 0x5B:
                print("Tilt query: Unexpected command indicator:", hex(response[1]))
                return None
            t_data = (response[2] << 8) | response[3]
        else:
            print("Tilt query: Incomplete response:", response.hex())
            return None

        if t_data > 18000:
            return (36000 - t_data) / 100.0
        else:
            return -t_data / 100.0

    def query_position(self):
        pan = self.query_pan_position()
        tilt = self.query_tilt_position()
        return (pan, tilt)

    def wait_for_position_settled(self, poll_interval=0.2, stable_time=1.0, tolerance=0.1):
        print("Waiting for position to settle...")
        last_pan, last_tilt = None, None
        stable_start = time.time()
        while True:
            pos = self.query_position()
            if pos[0] is None or pos[1] is None:
                print("Error querying position, retrying...")
                time.sleep(poll_interval)
                continue
            pan, tilt = pos
            if last_pan is not None and last_tilt is not None:
                if abs(pan - last_pan) < tolerance and abs(tilt - last_tilt) < tolerance:
                    if time.time() - stable_start >= stable_time:
                        print(f"Position settled: Pan = {pan}°, Tilt = {tilt}°")
                        break
                else:
                    stable_start = time.time()
            else:
                stable_start = time.time()
            last_pan, last_tilt = pan, tilt
            time.sleep(poll_interval)

    # =============================
    #      Basic Movement
    # =============================
    def move_up(self, speed=0x20):
        cmd = self.create_command(0x00, 0x08, 0x00, speed)
        self.send_command(cmd)

    def move_down(self, speed=0x20):
        cmd = self.create_command(0x00, 0x10, 0x00, speed)
        self.send_command(cmd)

    def move_left(self, speed=0x20):
        cmd = self.create_command(0x00, 0x04, speed, 0x00)
        self.send_command(cmd)

    def move_right(self, speed=0x20):
        cmd = self.create_command(0x00, 0x02, speed, 0x00)
        self.send_command(cmd)

    def stop(self):
        cmd = self.create_command(0x00, 0x00, 0x00, 0x00)
        self.send_command(cmd)

    def move_left_up(self, pan_speed=0x20, tilt_speed=0x20):
        cmd = self.create_command(0x00, 0x0C, pan_speed, tilt_speed)
        self.send_command(cmd)

    def move_left_down(self, pan_speed=0x20, tilt_speed=0x20):
        cmd = self.create_command(0x00, 0x14, pan_speed, tilt_speed)
        self.send_command(cmd)

    def move_right_up(self, pan_speed=0x20, tilt_speed=0x20):
        cmd = self.create_command(0x00, 0x0A, pan_speed, tilt_speed)
        self.send_command(cmd)

    def move_right_down(self, pan_speed=0x20, tilt_speed=0x20):
        cmd = self.create_command(0x00, 0x12, pan_speed, tilt_speed)
        self.send_command(cmd)

    # =============================
    #   Absolute Positioning with Blocking Option
    # =============================
    def absolute_pan(self, angle):
        """
        Move to an absolute pan position.
        For angles < 0, converts to the equivalent positive value (e.g. -5° becomes 355°).
        If blocking is enabled, this method waits until the encoder reports the target.
        """
        if angle < 0:
            value = 36000 - int(abs(angle) * 100)
        else:
            value = int(angle * 100)
        data1 = (value >> 8) & 0xFF
        data2 = value & 0xFF
        cmd = self.create_command(0x00, 0x4B, data1, data2)
        self.send_command(cmd)
        if self.blocking:
            self._wait_for_pan(angle, tolerance=0.2, max_wait=5.0)

    def absolute_tilt(self, angle):
        """
        Move to an absolute tilt position.
        For negative angles: value = abs(angle) * 100.
        For positive angles: value = 36000 - int(angle * 100).
        If blocking is enabled, this method waits until the encoder reports the target.
        """
        if angle < 0:
            value = int(abs(angle) * 100)
        else:
            value = 36000 - int(angle * 100)
        data1 = (value >> 8) & 0xFF
        data2 = value & 0xFF
        cmd = self.create_command(0x00, 0x4D, data1, data2)
        self.send_command(cmd)
        if self.blocking:
            self._wait_for_tilt(angle, tolerance=0.2, max_wait=5.0)

    def _wait_for_pan(self, angle, tolerance=0.2, max_wait=5.0):
        """
        Block until the pan encoder reading is within tolerance of the target.
        Converts a negative angle to its equivalent positive value.
        """
        target = angle if angle >= 0 else 360 + angle
        start_time = time.time()
        current_pan = None
        while time.time() - start_time < max_wait:
            current_pan = self.query_pan_position()
            if current_pan is not None:
                diff = abs(current_pan - target)
                if diff > 180:
                    diff = 360 - diff
                if diff <= tolerance:
                    print(f"Blocking: reached pan {current_pan:.2f}° (target {target}°)")
                    return current_pan
            time.sleep(0.05)
        print(f"Blocking timeout: pan did not reach {target}° within {max_wait} seconds.")
        return current_pan

    def _wait_for_tilt(self, angle, tolerance=0.2, max_wait=5.0):
        """
        Block until the tilt encoder reading is within tolerance of the target.
        """
        start_time = time.time()
        current_tilt = None
        while time.time() - start_time < max_wait:
            current_tilt = self.query_tilt_position()
            if current_tilt is not None:
                if abs(current_tilt - angle) <= tolerance:
                    print(f"Blocking: reached tilt {current_tilt:.2f}° (target {angle}°)")
                    return current_tilt
            time.sleep(0.05)
        print(f"Blocking timeout: tilt did not reach {angle}° within {max_wait} seconds.")
        return current_tilt

    # =============================
    #      Preset Management
    # =============================
    def set_preset(self, preset):
        cmd = self.create_command(0x00, 0x03, 0x00, preset)
        self.send_command(cmd)

    def call_preset(self, preset):
        cmd = self.create_command(0x00, 0x07, 0x00, preset)
        self.send_command(cmd)

    def delete_preset(self, preset):
        cmd = self.create_command(0x00, 0x05, 0x00, preset)
        self.send_command(cmd)

    # =============================
    #     Auxiliary Controls
    # =============================
    def open_aux(self, aux_value=0x00):
        cmd = self.create_command(0x00, 0x09, 0x00, aux_value)
        self.send_command(cmd)

    def shut_aux(self, aux_value=0x00):
        cmd = self.create_command(0x00, 0x0B, 0x00, aux_value)
        self.send_command(cmd)

    # =============================
    #      Optical Controls
    # =============================
    def zoom_in(self):
        cmd = self.create_command(0x00, 0x20, 0x00, 0x00)
        self.send_command(cmd)

    def zoom_out(self):
        cmd = self.create_command(0x00, 0x40, 0x00, 0x00)
        self.send_command(cmd)

    def focus_far(self):
        cmd = self.create_command(0x00, 0x80, 0x00, 0x00)
        self.send_command(cmd)

    def focus_near(self):
        cmd = self.create_command(0x01, 0x00, 0x00, 0x00)
        self.send_command(cmd)

    def iris_open(self):
        cmd = self.create_command(0x02, 0x00, 0x00, 0x00)
        self.send_command(cmd)

    def iris_shut(self):
        cmd = self.create_command(0x04, 0x00, 0x00, 0x00)
        self.send_command(cmd)

    # =============================
    #      Cruising Functions
    # =============================
    def start_cruise(self):
        cmd = self.create_command(0x00, 0x07, 0x00, 0x62)
        self.send_command(cmd)

    def set_cruise_dwell_time(self, dwell_time):
        cmd = self.create_command(0x00, 0x03, 0x00, dwell_time)
        self.send_command(cmd)

    def set_cruise_speed(self, speed):
        cmd = self.create_command(0x00, 0x03, 0x00, speed)
        self.send_command(cmd)

    # =============================
    #      Line Scan Functions
    # =============================
    def set_line_scan_start(self):
        cmd = self.create_command(0x00, 0x03, 0x00, 0x5C)
        self.send_command(cmd)

    def set_line_scan_end(self):
        cmd = self.create_command(0x00, 0x03, 0x00, 0x5D)
        self.send_command(cmd)

    def run_line_scan(self):
        cmd = self.create_command(0x00, 0x07, 0x00, 0x63)
        self.send_command(cmd)

    def set_line_scan_speed(self, speed):
        cmd = self.create_command(0x00, 0x03, 0x00, speed)
        self.send_command(cmd)

    # =============================
    #      Guard Location
    # =============================
    def enable_guard(self):
        cmd = self.create_command(0x00, 0x03, 0x00, 0x5E)
        self.send_command(cmd)

    def disable_guard(self):
        cmd = self.create_command(0x00, 0x07, 0x00, 0x5E)
        self.send_command(cmd)

    def set_guard_location_time(self, time_val):
        cmd = self.create_command(0x00, 0x03, 0x00, time_val)
        self.send_command(cmd)

    # =============================
    #  Real-Time Angle Feedback (Internal Callback)
    # =============================
    def _feedback_listener(self):
        while self.rt_feedback_active:
            try:
                if self.ser.in_waiting:
                    data = self.ser.read(self.ser.in_waiting)
                    try:
                        decoded_data = data.decode('ascii', errors='replace')
                    except Exception:
                        decoded_data = data.hex()
                    self.rt_callback(decoded_data)
                time.sleep(0.1)
            except Exception as e:
                print("Error in feedback listener:", e)
                break

    def enable_rt_feedback(self):
        self.rt_feedback_active = True
        cmd = self.create_command(0x00, 0x03, 0x00, 0x69)
        self.send_command(cmd)
        self.feedback_thread = threading.Thread(target=self._feedback_listener, daemon=True)
        self.feedback_thread.start()

    def disable_rt_feedback(self):
        self.rt_feedback_active = False
        if self.feedback_thread is not None:
            self.feedback_thread.join(timeout=1)
        cmd = self.create_command(0x00, 0x07, 0x00, 0x69)
        self.send_command(cmd)

    # =============================
    #  Remote Reset & Factory Default
    # =============================
    def remote_reset(self):
        cmd = self.create_command(0x00, 0x0F, 0x00, 0x00)
        self.send_command(cmd)

    def factory_default(self):
        cmds = [
            self.create_command(0x00, 0x03, 0x00, 0x5A),
            self.create_command(0x00, 0x07, 0x00, 0x5A),
            self.create_command(0x00, 0x03, 0x00, 0xFF),
            self.create_command(0x00, 0x07, 0x00, 0xFF)
        ]
        for cmd in cmds:
            self.send_command(cmd)
            time.sleep(0.1)

    def close(self):
        if self.ser and self.ser.is_open:
            self.ser.close()
            print("Serial port closed.")


# When run as a script, create an instance with blocking enabled.
if __name__ == '__main__':
    controller = PelcoDController(port='COM3', baudrate=9600, address=1, blocking=True)

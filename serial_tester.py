#!/usr/bin/env python3
"""
serial_tester.py
================
One-shot diagnostic for the BIT-PT850 pan/tilt head.

  1.  Opens the serial port using settings from YAML (or CLI overrides)
  2.  Lets PTZController run its zero-point routine
  3.  Queries pan and tilt multiple times, prints raw value + degrees
  4.  Closes the connection
  5.  Exits with non-zero code on any timeout / init failure

Example
--------
    python serial_tester.py --port COM3 --baud 9600 --addr 1
"""

from __future__ import annotations
import argparse
import logging
import sys
import time
from pathlib import Path
from typing import Dict, Any, List, Tuple

# ─────────────────────────── project imports ──────────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parent))   # ensure local pkg

from src.utils import load_config, get_connection_config          # type: ignore
from src.controller.ptz import PTZController                      # type: ignore

# ─────────────────────────── logging setup ────────────────────────────────
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)-8s| %(message)s")
log = logging.getLogger("serial_tester")
# ──────────────────────────────────────────────────────────────────────────


def cli() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="BIT-PT850 serial tester")
    p.add_argument("--config", help="YAML file (default: config/settings.yaml)")
    p.add_argument("--port", help="Serial port override, e.g. COM3")
    p.add_argument("--baud", type=int, help="Baud rate override (default 9600)")
    p.add_argument("--addr", type=int, default=1,
                   help="Pelco-D address (1-255, default 1)")
    return p.parse_args()


# ─────────────────────────── main routine ────────────────────────────────
def main() -> int:
    args = cli()

    # 1) load YAML (optional) ------------------------------------------------
    cfg_file = Path(args.config or "config/settings.yaml")
    cfg: Dict[str, Any] = load_config(cfg_file) if cfg_file.exists() else {}

    # 2) build flat connection dict -----------------------------------------
    conn_cfg = get_connection_config(cfg)
    # unwrap nested  connection: {serial: {...}}  form if present
    if "serial" in conn_cfg:
        conn_cfg = conn_cfg["serial"]

    # CLI overrides
    if args.port:
        conn_cfg["port"] = args.port
    if args.baud:
        conn_cfg["baudrate"] = args.baud

    log.info("Opening controller on %s @ %s bps",
             conn_cfg.get("port"), conn_cfg.get("baudrate"))

    # 3) instantiate controller --------------------------------------------
    try:
        ctrl = PTZController(connection_config=conn_cfg, address=args.addr)
    except Exception as exc:
        log.error("Failed to initialise PTZController: %s", exc, exc_info=True)
        return 1

    # 4) query multiple times ----------------------------------------------
    try:
        num_queries = 5
        pan_results: List[Tuple[int, float]] = []
        tilt_results: List[Tuple[int, float]] = []
        
        # Add initial delay for device to settle
        time.sleep(0.5)
        
        # Query pan positions
        print(f"\n===== QUERYING PAN POSITION ({num_queries} times) =====")
        for i in range(num_queries):
            print(f"[INFO] Pan query #{i+1}...")
            pan_raw, pan_deg = ctrl.query_pan_position()
            pan_results.append((pan_raw, pan_deg))
            print(f"  Raw: 0x{pan_raw:04X}  →  {pan_deg:.2f}°")
            if i < num_queries - 1:  # Don't delay after last query
                time.sleep(0.5)
        
        # Add delay between pan and tilt queries
        time.sleep(0.5)
        
        # Query tilt positions
        print(f"\n===== QUERYING TILT POSITION ({num_queries} times) =====")
        for i in range(num_queries):
            print(f"[INFO] Tilt query #{i+1}...")
            tilt_raw, tilt_deg = ctrl.query_tilt_position()
            tilt_results.append((tilt_raw, tilt_deg))
            print(f"  Raw: 0x{tilt_raw:04X}  →  {tilt_deg:.2f}°")
            if i < num_queries - 1:  # Don't delay after last query
                time.sleep(0.5)
        
        # Summary of results
        print("\n===== DEVICE POSITION SUMMARY =====")
        print("Pan positions:")
        for i, (raw, deg) in enumerate(pan_results):
            print(f"  #{i+1}: Raw 0x{raw:04X}  →  {deg:.2f}°")
            
        print("\nTilt positions:")
        for i, (raw, deg) in enumerate(tilt_results):
            print(f"  #{i+1}: Raw 0x{raw:04X}  →  {deg:.2f}°")
        print("==================================\n")

        # Flush remaining buffer data
        time.sleep(0.5)  # Add delay before flushing buffer
        print("===== FLUSHING REMAINING BUFFER DATA =====")
        try:
            remaining_data = ctrl.connection.receive(size=1024, timeout=0.5)
            if remaining_data:
                print(f"Remaining bytes: {' '.join(f'{b:02X}' for b in remaining_data)} | Length: {len(remaining_data)}")
            else:
                print("No remaining data in buffer")
        except Exception as e:
            print(f"Error flushing buffer: {e}")
        print("==========================================")

    except TimeoutError as exc:
        log.error("Timed out waiting for pan/tilt reply: %s", exc)
        return 2
    except Exception as exc:
        log.error("Unexpected error while querying: %s", exc, exc_info=True)
        return 3
    finally:
        ctrl.close()
        log.info("Closed connection")

    return 0

if __name__ == "__main__":
    exit_code = main()
    if not hasattr(sys, 'ps1'):  # Check if we're in interactive mode
        sys.exit(exit_code)
    # Don't call sys.exit in interactive mode
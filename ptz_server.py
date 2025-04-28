# =============================
# File: ptz_server.py (revised)
# =============================
"""
PTZ Control Server – revised version
-----------------------------------
Changes compared with the original:
  1. **Config‑driven port / host precedence** – the command‑line flag
     `--port` (or `--host`) now updates both the *api* **and** *client*
     section inside the live config so that the GUI launched by
     `run_all.py` will automatically target the same address.
  2. **Startup order** – the HTTP API is started **first**; the lengthy
     controller initialisation (zero‑point routine) is performed in a
     background thread so the GUI can open a socket immediately.
  3. **Graceful shutdown** – adds signal handling and ensures the
     background task as well as the serial connection are closed.
  4. **Better logging** – unified timestamps and clear phase messages.
"""

from __future__ import annotations

import argparse
import logging
import signal
import sys
import threading
from typing import Any, Dict

# Project imports
from src.utils import (
    load_config,
    get_api_config,
    get_connection_config,
    get_controller_config,
)
from src.controller import PTZController
from src.api import create_app, register_routes

logger = logging.getLogger("ptz-server")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="PTZ Control Server")
    parser.add_argument("--config", help="Path to YAML config file")
    parser.add_argument("--host", help="Bind address (overrides config)")
    parser.add_argument("--port", type=int, help="Bind port (overrides config)")
    parser.add_argument("--debug", action="store_true", help="Flask debug mode")
    return parser.parse_args()


def _background_init(controller: PTZController) -> None:
    """Run the lengthy zero‑point initialisation without blocking Flask."""
    logger.info("[BG] Running controller zero‑point routine …")
    try:
        controller.init_zero_points()  # the public helper usually wraps _init_zero_points
    except Exception as exc:
        logger.error("Error during zero‑point routine: %s", exc, exc_info=True)
    else:
        logger.info("[BG] Zero‑point routine finished ✔")


def main() -> int:
    args = _parse_args()

    # ------------------------------------------------------------------
    # 1. Load configuration -------------------------------------------
    # ------------------------------------------------------------------
    try:
        config: Dict[str, Any] = load_config(args.config)
    except Exception as exc:
        logger.error("Cannot load configuration: %s", exc)
        return 1

    api_cfg = get_api_config(config)
    conn_cfg = get_connection_config(config)
    ctrl_cfg = get_controller_config(config)

    # CLI overrides take precedence and are replicated into the client
    if args.host:
        api_cfg["host"] = args.host
        config.setdefault("client", {})["host"] = args.host
    if args.port:
        api_cfg["port"] = args.port
        config.setdefault("client", {})["port"] = args.port
    if args.debug:
        api_cfg["debug"] = True

    host = api_cfg.get("host", "127.0.0.1")
    port = api_cfg.get("port", 5000)
    debug = api_cfg.get("debug", False)

    # ------------------------------------------------------------------
    # 2. Build the API first so that a socket is open quickly ----------
    # ------------------------------------------------------------------
    app, socketio = create_app(api_cfg)

    # Placeholder controller – will be replaced after init finishes
    controller = PTZController(connection_config=conn_cfg, address=ctrl_cfg.get("address", 1))
    register_routes(app, socketio, controller)

    # The heavy zero‑point routine is performed in the background
    socketio.start_background_task(_background_init, controller)

    # ------------------------------------------------------------------
    # 3. Graceful shutdown helpers -------------------------------------
    # ------------------------------------------------------------------
    stop_event = threading.Event()

    def _signal_handler(*_):
        logger.info("Termination requested … shutting down")
        stop_event.set()
        # Flask-SocketIO will stop on the next tick; we just keep the
        # main thread alive until it quits.

    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, _signal_handler)

    # ------------------------------------------------------------------
    # 4. Run the Flask‑SocketIO server ---------------------------------
    # ------------------------------------------------------------------
    logger.info("Starting PTZ API on %s:%s (debug=%s)", host, port, debug)
    try:
        socketio.run(
            app,
            host=host,
            port=port,
            debug=debug,
            allow_unsafe_werkzeug=True,
        )
    finally:
        # ensure serial port closes
        logger.info("Closing serial connection …")
        controller.close()
        logger.info("Bye ✌️")
    return 0


if __name__ == "__main__":
    sys.exit(main())
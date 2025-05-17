# =============================
# File: ptz_server.py (revised)
# =============================
"""
PTZ Control Server – revised version
-----------------------------------
Changes compared with the original:
  1. **Config‑driven initialization** – uses only the YAML config file
     with no command-line arguments.
  2. **Startup order** – the HTTP API is started **first**; the lengthy
     controller initialisation (zero‑point routine) is performed in a
     background thread so the GUI can open a socket immediately.
  3. **Graceful shutdown** – adds signal handling and ensures the
     background task as well as the serial connection are closed.
  4. **Better logging** – unified timestamps and clear phase messages.
"""

from __future__ import annotations

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


def _background_init(controller: PTZController) -> None:
    """
    Previously ran the zero-point initialization.
    Now just logs that initialization is skipped as per requirements.
    """
    logger.info("[BG] Controller zero-point initialization is disabled")
    # No initialization is performed - controller will run without offset correction


def main() -> int:
    # ------------------------------------------------------------------
    # 1. Load configuration -------------------------------------------
    # ------------------------------------------------------------------
    try:
        config: Dict[str, Any] = load_config()
    except Exception as exc:
        logger.error("Cannot load configuration: %s", exc)
        return 1

    api_cfg = get_api_config(config)
    conn_cfg = get_connection_config(config)
    ctrl_cfg = get_controller_config(config)

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
            use_reloader=False,  # Disable auto-reloading to prevent port conflicts
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

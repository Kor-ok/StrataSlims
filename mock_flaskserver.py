"""
Lightweight auxiliary Flask server for StrataSlims.

Goals
- Run asynchronously in a background thread so it does not block the Discord bot.
- Provide simple health and shutdown endpoints.
- Allow an optional shutdown callback to be invoked when the shutdown route is hit
  (e.g., to initiate graceful bot shutdown), but default to shutting down only this
  HTTP server.

Usage
	from mock_flaskserver import start_background_server, stop_server

	# Start the server in the background (won't block the bot)
	start_background_server(host="127.0.0.1", port=8787)

	# ... later, to stop programmatically (same as posting to /shutdown):
	stop_server()

Environment
- FLASK_SHUTDOWN_TOKEN (optional): if set, required for POST /shutdown requests.
  Provide token via either:
	- HTTP header:  Authorization: Bearer <token>
	- Query param:  /shutdown?token=<token>

Endpoints
- GET  /health           -> {"status": "ok"}
- POST /shutdown         -> {"status": "stopping"}
"""

from __future__ import annotations

import os
import threading
import time
from typing import Callable, Optional

from flask import Flask, abort, jsonify, request
from werkzeug.serving import make_server

from config import get_flask_shutdown_token

# Flask application
app = Flask("strataslims-aux")


# Server state (module-level to keep things simple)
_http_server = None  # type: Optional[object]
_server_thread: Optional[threading.Thread] = None
_shutdown_cb: Optional[Callable[[], None]] = None
_token: Optional[str] = get_flask_shutdown_token()


def _is_authorized(req) -> bool:
	"""Validate optional token when configured."""
	if not _token:
		return True
	# Header takes precedence
	auth = req.headers.get("Authorization", "")
	if auth.startswith("Bearer ") and auth[7:] == _token:
		return True
	# Fallback to query param
	if req.args.get("token") == _token:
		return True
	return False


@app.get("/health")
def health():
	return jsonify({"status": "ok"}), 200


@app.post("/shutdown")
def shutdown():
	if not _is_authorized(request):
		abort(403)

	# Optionally invoke caller-provided shutdown hook (non-blocking)
	if _shutdown_cb:
		threading.Thread(target=_shutdown_cb, name="aux-shutdown-callback", daemon=True).start()

	# Stop the HTTP server shortly after sending the response
	def _delayed_stop():
		# Give the response a moment to flush
		time.sleep(1)
		stop_server()

	threading.Thread(target=_delayed_stop, name="aux-http-stop", daemon=True).start()
	return jsonify({"status": "stopping"}), 202

@app.post("/startbot")
def startbot():
	if not _is_authorized(request):
		abort(403)

	return jsonify({"status": "not implemented"}), 501

@app.post("/stopbot")
def stopbot():
	if not _is_authorized(request):
		abort(403)

	return jsonify({"status": "not implemented"}), 501

@app.post("/restartbot")
def restartbot():
	if not _is_authorized(request):
		abort(403)

	return jsonify({"status": "not implemented"}), 501

def start_background_server(host: str = "127.0.0.1", port: int = 8787, *,
							shutdown_callback: Optional[Callable[[], None]] = None,
							token: Optional[str] = None) -> None:
	"""Start the Flask server in a background thread.

	- host: Interface to bind (default 127.0.0.1).
	- port: Port to listen on (default 8787).
	- shutdown_callback: Optional function invoked when /shutdown is posted.
	- token: Optional token to require for /shutdown; overrides env if provided.
	"""
	global _http_server, _server_thread, _shutdown_cb, _token

	if is_running():
		return

	_shutdown_cb = shutdown_callback
	if token is not None:
		_token = token

	# Create a WSGI server so we can control lifecycle programmatically.
	_http_server = make_server(host, port, app)

	def _serve_forever():
		try:
			_http_server.serve_forever()  # type: ignore[attr-defined]
		except Exception:
			# Suppress noisy exceptions during shutdown
			pass

	_server_thread = threading.Thread(target=_serve_forever, name="strataslims-aux-http", daemon=True)
	_server_thread.start()


def stop_server() -> None:
	"""Stop the HTTP server if running."""
	global _http_server, _server_thread
	srv = _http_server
	thr = _server_thread
	_http_server = None
	_server_thread = None
	if srv is not None:
		try:
			srv.shutdown()  # type: ignore[attr-defined]
		except Exception:
			pass
	if thr is not None and thr.is_alive():
		try:
			thr.join(timeout=2)
		except Exception:
			pass


def is_running() -> bool:
	"""Return True if the background server thread is active."""
	return _server_thread is not None and _server_thread.is_alive()


if __name__ == "__main__":
	# Manual local run for debugging; Ctrl+C to stop
	start_background_server()
	try:
		while True:
			time.sleep(1)
	except KeyboardInterrupt:
		stop_server()
		print("Aux Flask server stopped.")

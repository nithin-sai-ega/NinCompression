"""
Simple web adapter for NinCompression.

Implements minimal HTTP endpoints using only the Python standard library.
Endpoints (POST, multipart/form-data):
  - /compress    (file, algorithm, level, output_format)
  - /decompress  (file)
  - /info        (file)

Responses carry permissive CORS headers so the React UI (served from another
port during development) can call the server from the browser. By default the
server only listens on localhost.
"""

from __future__ import annotations

import io
import json
import zipfile
from email.parser import BytesParser
from email.policy import HTTP
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Dict

from main import AUTO, compress_file, decompress_file, get_file_info
from compressor import available_algorithms

ALGORITHMS = set(available_algorithms()) | {AUTO}
MAX_UPLOAD_BYTES = 64 * 1024 * 1024  # refuse uploads larger than this


class _RequestError(Exception):
    """A problem with the request itself; carries the HTTP status to send."""

    def __init__(self, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.status = status


def _normalize_algorithm(value: str) -> str:
    return value.strip().lower()


def _parse_int(value: str, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def parse_multipart(content_type: str, body: bytes) -> Dict[str, bytes]:
    """Parse a multipart/form-data body into {field name: raw bytes}."""
    if not content_type.lower().startswith("multipart/form-data"):
        raise _RequestError("Expected multipart/form-data.")
    message = BytesParser(policy=HTTP).parsebytes(
        b"Content-Type: " + content_type.encode("latin-1") + b"\r\nMIME-Version: 1.0\r\n\r\n" + body
    )
    if not message.is_multipart():
        raise _RequestError("Malformed multipart body.")
    fields: Dict[str, bytes] = {}
    for part in message.iter_parts():
        name = part.get_param("name", header="content-disposition")
        if name:
            fields[name] = part.get_payload(decode=True) or b""
    return fields


class AdapterHandler(BaseHTTPRequestHandler):
    def _cors_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Expose-Headers", "Content-Disposition")

    def _send_json(self, status: int, payload: dict) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self._cors_headers()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_file(self, filename: str, data: bytes, content_type: str) -> None:
        self.send_response(200)
        self._cors_headers()
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _read_form(self) -> Dict[str, bytes]:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            raise _RequestError("Invalid Content-Length.")
        if length <= 0:
            raise _RequestError("Empty request body.")
        if length > MAX_UPLOAD_BYTES:
            raise _RequestError("Upload too large.", status=413)
        body = self.rfile.read(length)
        return parse_multipart(self.headers.get("Content-Type", ""), body)

    @staticmethod
    def _text_field(form: Dict[str, bytes], name: str, default: str) -> str:
        value = form.get(name)
        return value.decode("utf-8", errors="replace") if value is not None else default

    @staticmethod
    def _upload(form: Dict[str, bytes]) -> bytes:
        if "file" not in form:
            raise _RequestError("Missing file upload.")
        return form["file"]

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(204)
        self._cors_headers()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_POST(self) -> None:  # noqa: N802
        try:
            self._handle_post()
        except _RequestError as exc:
            self._send_json(exc.status, {"error": str(exc)})
        except (ValueError, KeyError, OSError) as exc:
            self._send_json(400, {"error": str(exc.args[0] if exc.args else exc)})
        except Exception:  # pragma: no cover - last-resort guard
            self._send_json(500, {"error": "Internal server error."})

    def _handle_post(self) -> None:
        if self.path not in {"/compress", "/decompress", "/info"}:
            raise _RequestError("Unknown endpoint.", status=404)
        form = self._read_form()

        if self.path == "/compress":
            algo = _normalize_algorithm(self._text_field(form, "algorithm", AUTO))
            if algo not in ALGORITHMS:
                raise _RequestError(f"Unknown algorithm: {algo}")
            level = _parse_int(self._text_field(form, "level", "3"), default=3)
            output_format = self._text_field(form, "output_format", "nin").strip().lower()
            if output_format not in {"nin", "zip"}:
                raise _RequestError("output_format must be 'nin' or 'zip'.")

            out_bytes, out_name = compress_file(
                self._upload(form), algorithm=algo, level=level, output_format="nin"
            )
            if output_format == "zip":
                zip_buf = io.BytesIO()
                with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_STORED) as zf:
                    zf.writestr(out_name, out_bytes)
                self._send_file("output.zip", zip_buf.getvalue(), "application/zip")
            else:
                self._send_file(out_name, out_bytes, "application/octet-stream")
            return

        if self.path == "/decompress":
            out_bytes, out_name = decompress_file(self._upload(form))
            self._send_file(out_name, out_bytes, "application/octet-stream")
            return

        self._send_json(200, get_file_info(self._upload(form)))

    def log_message(self, format: str, *args) -> None:  # noqa: A002
        print(f"{self.address_string()} - {format % args}")


def make_server(host: str = "127.0.0.1", port: int = 8000) -> ThreadingHTTPServer:
    """Create (but do not start) the HTTP server."""
    return ThreadingHTTPServer((host, port), AdapterHandler)


def run(host: str = "127.0.0.1", port: int = 8000) -> None:
    """Start the HTTP server."""
    server = make_server(host, port)
    print(f"Listening on http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
    finally:
        server.server_close()


if __name__ == "__main__":
    run()

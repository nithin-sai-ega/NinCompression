import http.client
import json
import threading
import unittest
import uuid

from helpers import sample_inputs

from web_adapter import make_server


def multipart(fields, file_bytes=None):
    boundary = uuid.uuid4().hex
    parts = []
    for name, value in fields.items():
        parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode()
        )
    if file_bytes is not None:
        parts.append(
            (
                f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="f.bin"\r\n'
                "Content-Type: application/octet-stream\r\n\r\n"
            ).encode()
            + file_bytes
            + b"\r\n"
        )
    parts.append(f"--{boundary}--\r\n".encode())
    return f"multipart/form-data; boundary={boundary}", b"".join(parts)


class TestWebAdapter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = make_server("127.0.0.1", 0)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def post(self, path, fields, file_bytes=None):
        content_type, body = multipart(fields, file_bytes)
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=30)
        conn.request("POST", path, body=body, headers={"Content-Type": content_type})
        response = conn.getresponse()
        payload = response.read()
        headers = dict(response.getheaders())
        conn.close()
        return response.status, headers, payload

    def test_compress_then_decompress_roundtrip(self):
        data = sample_inputs()["text"]
        status, headers, packed = self.post("/compress", {"algorithm": "lz77h", "level": "3"}, data)
        self.assertEqual(status, 200)
        self.assertEqual(headers.get("Access-Control-Allow-Origin"), "*")
        self.assertLess(len(packed), len(data))

        status, _, restored = self.post("/decompress", {}, packed)
        self.assertEqual(status, 200)
        self.assertEqual(restored, data)

    def test_info_endpoint(self):
        data = b"hello hello hello hello"
        _, _, packed = self.post("/compress", {"algorithm": "rle"}, data)
        status, _, body = self.post("/info", {}, packed)
        info = json.loads(body)
        self.assertEqual(status, 200)
        self.assertEqual(info["algorithm"], "rle")
        self.assertEqual(info["original_size"], len(data))
        self.assertTrue(info["checksum_verified"])

    def test_unknown_algorithm_is_a_400(self):
        status, _, body = self.post("/compress", {"algorithm": "nope"}, b"abc")
        self.assertEqual(status, 400)
        self.assertIn("Unknown algorithm", json.loads(body)["error"])

    def test_invalid_level_is_a_400_not_a_dropped_connection(self):
        status, _, body = self.post("/compress", {"algorithm": "lz77", "level": "9"}, b"abc")
        self.assertEqual(status, 400)
        self.assertIn("level", json.loads(body)["error"])

    def test_bad_nin_upload_is_a_400(self):
        status, _, body = self.post("/decompress", {}, b"definitely not a nin file")
        self.assertEqual(status, 400)
        self.assertIn("error", json.loads(body))

    def test_missing_file_is_a_400(self):
        status, _, body = self.post("/compress", {"algorithm": "rle"})
        self.assertEqual(status, 400)
        self.assertIn("Missing file", json.loads(body)["error"])

    def test_zip_output(self):
        status, headers, body = self.post(
            "/compress", {"algorithm": "rle", "output_format": "zip"}, b"aaaa"
        )
        self.assertEqual(status, 200)
        self.assertEqual(headers.get("Content-Type"), "application/zip")
        self.assertTrue(body.startswith(b"PK"))

    def test_unknown_endpoint_is_a_404(self):
        status, _, _ = self.post("/nope", {}, b"abc")
        self.assertEqual(status, 404)

    def test_preflight_request(self):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        conn.request("OPTIONS", "/compress")
        response = conn.getresponse()
        response.read()
        self.assertEqual(response.status, 204)
        self.assertEqual(response.getheader("Access-Control-Allow-Origin"), "*")
        conn.close()


if __name__ == "__main__":
    unittest.main()

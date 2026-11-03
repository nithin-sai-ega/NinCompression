import React, { useMemo, useRef, useState } from "react";

const ALGORITHMS = [
  { value: "auto", label: "Auto (smallest result)" },
  { value: "rle", label: "RLE" },
  { value: "huffman", label: "Huffman" },
  { value: "lz77", label: "LZ77" },
  { value: "lz77h", label: "LZ77+Huffman" },
  { value: "store", label: "Store (no compression)" }
];

const ENDPOINTS = {
  compress: "/compress",
  decompress: "/decompress"
};

function formatBytes(bytes) {
  if (bytes === null || bytes === undefined) return "—";
  const units = ["B", "KB", "MB", "GB"];
  let value = bytes;
  let i = 0;
  while (value >= 1024 && i < units.length - 1) {
    value /= 1024;
    i += 1;
  }
  return `${value.toFixed(value >= 10 || i === 0 ? 0 : 1)} ${units[i]}`;
}

export default function App() {
  const [file, setFile] = useState(null);
  const [algorithm, setAlgorithm] = useState("auto");
  const [level, setLevel] = useState(3);
  const [format, setFormat] = useState("nin");
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState("Idle");
  const [downloadUrl, setDownloadUrl] = useState("");
  const [downloadName, setDownloadName] = useState("");
  const [error, setError] = useState("");
  const [recentFiles, setRecentFiles] = useState([]);
  const [apiBaseUrl, setApiBaseUrl] = useState("http://localhost:8000");
  const [sizes, setSizes] = useState({
    original: null,
    compressed: null
  });
  const dropRef = useRef(null);

  const levelEnabled = useMemo(
    () => ["lz77", "lz77h", "auto"].includes(algorithm),
    [algorithm]
  );

  function pushRecent(entry) {
    setRecentFiles((prev) => [entry, ...prev].slice(0, 5));
  }

  function resetOutput() {
    if (downloadUrl) {
      URL.revokeObjectURL(downloadUrl);
    }
    setDownloadUrl("");
    setDownloadName("");
    setProgress(0);
    setSizes({ original: null, compressed: null });
  }

  function handleFileChange(event) {
    const selected = event.target.files?.[0] || null;
    setFile(selected);
    resetOutput();
  }

  function handleDrop(event) {
    event.preventDefault();
    const dropped = event.dataTransfer.files?.[0] || null;
    if (dropped) {
      setFile(dropped);
      resetOutput();
    }
    dropRef.current?.classList.remove("drag-over");
  }

  function handleDragOver(event) {
    event.preventDefault();
    dropRef.current?.classList.add("drag-over");
  }

  function handleDragLeave() {
    dropRef.current?.classList.remove("drag-over");
  }

  function showError(message) {
    setError(message);
    setStatus("Error");
    setTimeout(() => setError(""), 4000);
  }

  function buildFormData(includeFormat) {
    if (!file) {
      showError("Please choose a file first.");
      return null;
    }
    const data = new FormData();
    data.append("file", file);
    data.append("algorithm", algorithm);
    if (levelEnabled) {
      data.append("level", String(level));
    }
    if (includeFormat) {
      data.append("output_format", format);
    }
    return data;
  }

  function runRequest(endpoint, includeFormat) {
    const data = buildFormData(includeFormat);
    if (!data) return;
    resetOutput();
    setStatus("Working...");

    const xhr = new XMLHttpRequest();
    const url = `${apiBaseUrl.replace(/\/$/, "")}${endpoint}`;
    xhr.open("POST", url, true);
    xhr.responseType = "blob";

    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) {
        setProgress(Math.round((event.loaded / event.total) * 100));
      }
    };

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        const blob = xhr.response;
        const disposition = xhr.getResponseHeader("Content-Disposition") || "";
        const match = /filename="([^"]+)"/.exec(disposition);
        const name = match ? match[1] : "output.bin";
        const url = URL.createObjectURL(blob);
        setDownloadUrl(url);
        setDownloadName(name);
        setProgress(100);
        setStatus("Done");
        setSizes({
          original: file?.size ?? null,
          compressed: blob.size
        });
        pushRecent({
          name: file?.name || "upload",
          action: endpoint === ENDPOINTS.compress ? "Compressed" : "Decompressed",
          algorithm: algorithm,
          time: new Date().toLocaleTimeString()
        });
      } else {
        showError("Request failed. Check the server and file format.");
      }
    };

    xhr.onerror = () => {
      showError("Network error. Make sure the server is running.");
    };

    xhr.send(data);
  }

  const ratio = useMemo(() => {
    if (!sizes.original || !sizes.compressed) return "—";
    return (sizes.compressed / sizes.original).toFixed(2);
  }, [sizes]);

  return (
    <div className="page">
      <header className="hero">
        <div>
          <p className="eyebrow">NinCompression</p>
          <h1>File Compression Studio</h1>
          <p className="subhead">
            Compress and decompress files with RLE, Huffman and LZ77, all
            implemented from scratch.
          </p>
        </div>
        <div className="hero-card">
          <div className="metric">
            <span>Original</span>
            <strong>{formatBytes(sizes.original)}</strong>
          </div>
          <div className="metric">
            <span>Compressed</span>
            <strong>{formatBytes(sizes.compressed)}</strong>
          </div>
          <div className="metric">
            <span>Ratio</span>
            <strong>{ratio}</strong>
          </div>
        </div>
      </header>

      <main className="panel">
        <section className="api-config">
          <div className="field">
            <label htmlFor="apiBase">API Base URL</label>
            <input
              id="apiBase"
              type="url"
              placeholder="http://localhost:8000"
              value={apiBaseUrl}
              onChange={(event) => setApiBaseUrl(event.target.value)}
            />
            <small>Point this to your running web adapter server.</small>
          </div>
        </section>
        <section className="upload">
          <div
            className="dropzone"
            ref={dropRef}
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
          >
            <input id="file" type="file" onChange={handleFileChange} />
            <label htmlFor="file">
              <span>Drop a file here</span>
              <small>or click to browse (any file, or a .nin to decompress)</small>
            </label>
          </div>
          {file ? (
            <div className="file-row">
              <div>
                <strong>{file.name}</strong>
                <small>{formatBytes(file.size)}</small>
              </div>
              <button className="ghost" onClick={() => setFile(null)}>
                Clear
              </button>
            </div>
          ) : null}
        </section>

        <section className="controls">
          <div className="field">
            <label htmlFor="algorithm">Algorithm</label>
            <select
              id="algorithm"
              value={algorithm}
              onChange={(event) => setAlgorithm(event.target.value)}
            >
              {ALGORITHMS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="level">
              Compression Level <span>{level}</span>
            </label>
            <input
              id="level"
              type="range"
              min="1"
              max="5"
              value={level}
              disabled={!levelEnabled}
              onChange={(event) => setLevel(Number(event.target.value))}
            />
            <small>
              Used by LZ77, LZ77+Huffman and Auto. Higher is stronger but slower.
            </small>
          </div>
          <div className="field">
            <label htmlFor="format">Output format</label>
            <select
              id="format"
              value={format}
              onChange={(event) => setFormat(event.target.value)}
            >
              <option value="nin">.nin</option>
              <option value="zip">.zip</option>
            </select>
          </div>
        </section>

        <section className="actions">
          <button
            className="primary"
            onClick={() => runRequest(ENDPOINTS.compress, true)}
          >
            Compress
          </button>
          <button
            className="secondary"
            onClick={() => runRequest(ENDPOINTS.decompress, false)}
          >
            Decompress
          </button>
        </section>

        <section className="progress">
          <div className="progress-bar">
            <div className="progress-fill" style={{ width: `${progress}%` }} />
          </div>
          <div className="progress-meta">
            <span>{status}</span>
            <span>{progress}%</span>
          </div>
        </section>

        <section className="results">
          {downloadUrl ? (
            <a className="download" href={downloadUrl} download={downloadName}>
              Download {downloadName}
            </a>
          ) : (
            <span className="download muted">Download will appear here.</span>
          )}
        </section>

        <section className="recent">
          <div className="recent-header">
            <h2>Recent files</h2>
            <small>Last 5 actions in this session.</small>
          </div>
          {recentFiles.length === 0 ? (
            <p className="muted">No recent activity yet.</p>
          ) : (
            <ul>
              {recentFiles.map((item, index) => (
                <li key={`${item.name}-${index}`}>
                  <div>
                    <strong>{item.name}</strong>
                    <small>
                      {item.action} · {item.algorithm.toUpperCase()} · {item.time}
                    </small>
                  </div>
                  <span className="pill">{item.action}</span>
                </li>
              ))}
            </ul>
          )}
        </section>
      </main>

      {error ? <div className="toast">{error}</div> : null}
    </div>
  );
}

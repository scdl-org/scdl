import { html, render, useState, useEffect, useRef } from "./vendor/preact-htm.module.js";

// ---------------------------------------------------------------- helpers

const api = async (path, body) => {
  const res = await fetch(path, body === undefined ? {} : {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
  return data;
};

const isUrl = (s) => /^(https?:\/\/)?([\w-]+\.)?soundcloud\.com\//i.test(s.trim());

const fmtDur = (s) => {
  if (!s && s !== 0) return "";
  s = Math.round(s);
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), sec = s % 60;
  const pad = (n) => String(n).padStart(2, "0");
  return h ? `${h}:${pad(m)}:${pad(sec)}` : `${m}:${pad(sec)}`;
};
const fmtNum = (n) => {
  if (n == null) return "";
  if (n >= 1e6) return (n / 1e6).toFixed(1).replace(/\.0$/, "") + "M";
  if (n >= 1e3) return (n / 1e3).toFixed(1).replace(/\.0$/, "") + "k";
  return String(n);
};
const fmtSpeed = (b) => (b ? `${(b / 1048576).toFixed(1)} MB/s` : "");
const basename = (p) => (p || "").split(/[\\/]/).pop();

const store = {
  get(key, fallback) {
    try { const v = localStorage.getItem(key); return v ? { ...fallback, ...JSON.parse(v) } : fallback; }
    catch { return fallback; }
  },
  set(key, value) { try { localStorage.setItem(key, JSON.stringify(value)); } catch { /* ignore */ } },
};

const KIND_LABEL = { track: "Pista", playlist: "Playlist", album: "Álbum", user: "Usuario" };
const STATUS_LABEL = {
  queued: "En cola", running: "Descargando", done: "Listo", error: "Error", cancelled: "Cancelado",
  downloading: "Descargando", processing: "Procesando", exists: "Ya existía",
  preparing: "Preparando", skipped: "Omitida",
};

const DEFAULT_OPTIONS = {
  path: "",
  audio_format: "",
  audio_quality: "",
  max_tracks: "",
  offset: "",
  min_duration: "",
  max_duration: "",
  sleep: "",
  parallel: "3",
  continue: true,
  clean_tags: true,
  only_new: false,
  skip_known_drm: true,
  write_cover: false,
  add_description: false,
  no_playlist_folder: false,
  original_art: false,
  extract_artist: false,
  only_original: false,
  no_original: false,
  opus: false,
  flac: false,
};

const FORMATS = [
  ["", "Original"], ["mp3", "MP3"], ["m4a", "M4A"], ["opus", "Opus"], ["flac", "FLAC"],
];
const QUALITIES = {
  mp3: [["", "Mejor VBR"], ["320K", "320k"], ["256K", "256k"], ["192K", "192k"], ["128K", "128k"]],
  m4a: [["", "Auto"], ["256K", "256k"], ["192K", "192k"], ["128K", "128k"]],
  opus: [["", "Auto"], ["192K", "192k"], ["128K", "128k"], ["96K", "96k"]],
};

// ---------------------------------------------------------------- components

function Art({ src, kind, size }) {
  const cls = `art ${size || ""} ${kind === "user" ? "round" : ""}`;
  return src ? html`<img class=${cls} src=${src} alt="" loading="lazy" />` : html`<div class=${cls}></div>`;
}

function ItemMeta({ it }) {
  return html`<div class="meta">
    <span class="badge ${it.kind === "user" ? "" : "accent"}">${KIND_LABEL[it.kind] || it.kind}</span>
    ${it.user && html`<span>${it.user}</span>`}
    ${it.kind === "track" && it.duration ? html`<span>${fmtDur(it.duration)}</span>` : null}
    ${it.track_count != null && it.kind !== "track" ? html`<span>${it.track_count} pistas</span>` : null}
    ${it.followers != null ? html`<span>${fmtNum(it.followers)} seguidores</span>` : null}
    ${it.plays != null ? html`<span>${fmtNum(it.plays)} plays</span>` : null}
    ${it.policy === "SNIP" ? html`<span class="badge warn" title="Solo vista previa sin cuenta Go+">Go+</span>` : null}
    ${it.policy === "BLOCK" ? html`<span class="badge warn">Bloqueada</span>` : null}
  </div>`;
}

function userModes(it) {
  return [
    ["tracks", "Subidas", it.track_count],
    ["likes", "Likes", it.likes_count],
    ["reposts", "Reposts", it.reposts_count],
    ["all", "Subidas + reposts", null],
    ["playlists", "Playlists", it.playlist_count],
    ["comments", "Comentadas", it.comments_count],
  ];
}

function Seg({ value, options, onChange }) {
  return html`<div class="seg">${options.map(([v, label]) => html`
    <button type="button" class=${value === v ? "on" : ""} onClick=${() => onChange(v)}>${label}</button>`)}
  </div>`;
}

function Check({ opts, set, name, label, hint }) {
  return html`<label class="check">
    <input type="checkbox" checked=${!!opts[name]} onChange=${(e) => set({ [name]: e.target.checked })} />
    <span>${label}${hint && html`<small>${hint}</small>`}</span>
  </label>`;
}

function Field({ opts, set, name, label, placeholder, wide, type = "text" }) {
  return html`<div class="field ${wide ? "wide" : ""}">
    <label>${label}</label>
    <input type=${type} min="1" value=${opts[name]} placeholder=${placeholder || ""}
      onInput=${(e) => set({ [name]: e.target.value })} />
  </div>`;
}

function FolderField({ opts, set, config }) {
  const [picking, setPicking] = useState(false);
  const [error, setError] = useState("");
  const fallback = config ? config.download_dir : "";

  const browse = async () => {
    setPicking(true); setError("");
    try {
      const { path } = await api("/api/pick-folder", { initial: opts.path || fallback });
      if (path) set({ path });
    } catch (err) {
      setError(err.message);
    } finally {
      setPicking(false);
    }
  };

  return html`<div class="field wide">
    <label>Carpeta de destino</label>
    <div class="row">
      <input type="text" value=${opts.path} placeholder=${fallback}
        onInput=${(e) => set({ path: e.target.value })} />
      <button type="button" class="btn" onClick=${browse} disabled=${picking}>
        ${picking ? html`<span class="spinner"></span> Eligiendo…` : "Examinar…"}
      </button>
    </div>
    ${picking && html`<div class="muted small" style="margin-top:4px">
      Se abrió el selector de carpetas de Windows (puede estar detrás de esta ventana).</div>`}
    ${error && html`<div class="error-msg">${error}</div>`}
  </div>`;
}

function Options({ opts, set, config, isCollection }) {
  const qualities = QUALITIES[opts.audio_format];
  return html`<div class="panel">
    <h2>Opciones</h2>
    <div class="options">
      <${FolderField} opts=${opts} set=${set} config=${config} />
      <div class="field wide">
        <span class="lbl">Formato</span>
        <${Seg} value=${opts.audio_format} options=${FORMATS}
          onChange=${(v) => set({ audio_format: v, audio_quality: "" })} />
      </div>
      ${qualities && html`<div class="field wide">
        <span class="lbl">Calidad</span>
        <${Seg} value=${opts.audio_quality} options=${qualities} onChange=${(v) => set({ audio_quality: v })} />
      </div>`}
      ${!opts.audio_format && html`<div class="field wide muted small">
        Original = el mejor stream disponible sin recomprimir (o el archivo original si el artista lo permite).
        Convertir a MP3 320k no mejora la calidad de origen.
      </div>`}
      ${isCollection && html`
        <${Field} opts=${opts} set=${set} name="max_tracks" label="Máx. pistas (-n)" type="number" placeholder="todas" />
        <${Field} opts=${opts} set=${set} name="offset" label="Empezar en (-o)" type="number" placeholder="1" />`}
      <${Field} opts=${opts} set=${set} name="min_duration" label="Duración mínima" placeholder="ej. 1:00" />
      <${Field} opts=${opts} set=${set} name="max_duration" label="Duración máxima" placeholder="ej. 10:00" />
      <${Field} opts=${opts} set=${set} name="sleep" label="Pausa entre peticiones (s)" type="number" placeholder="0" />
      ${isCollection && html`<div class="field">
        <span class="lbl">Pistas a la vez</span>
        <${Seg} value=${String(opts.parallel || "1")} options=${[["1", "1"], ["2", "2"], ["3", "3"]]}
          onChange=${(v) => set({ parallel: v })} />
      </div>`}
    </div>
    <div class="checks">
      <${Check} opts=${opts} set=${set} name="clean_tags" label="Limpiar artista/título" hint="«Artista - Título», feat., sin [Free Download]…" />
      <${Check} opts=${opts} set=${set} name="continue" label="Saltar archivos existentes" hint="Continúa si el archivo ya existe (-c)" />
      <${Check} opts=${opts} set=${set} name="only_new" label="Solo nuevas" hint="Historial scdl-archive.txt en la carpeta" />
      <${Check} opts=${opts} set=${set} name="skip_known_drm" label="Saltar pistas con DRM" hint="Y recordarlas para no reintentar" />
      <${Check} opts=${opts} set=${set} name="write_cover" label="Guardar portada aparte" hint="Además de incrustarla" />
      <${Check} opts=${opts} set=${set} name="add_description" label="Descripción en .txt" />
      <${Check} opts=${opts} set=${set} name="no_playlist_folder" label="Sin subcarpeta de playlist" />
    </div>
    <details>
      <summary>Avanzado</summary>
      <div class="checks">
        <${Check} opts=${opts} set=${set} name="original_art" label="Portada a resolución original" />
        <${Check} opts=${opts} set=${set} name="extract_artist" label="Artista desde el título" hint="«Artista - Título»" />
        <${Check} opts=${opts} set=${set} name="only_original" label="Solo archivos originales" />
        <${Check} opts=${opts} set=${set} name="no_original" label="Nunca el archivo original" />
        <${Check} opts=${opts} set=${set} name="opus" label="Preferir Opus" />
        <${Check} opts=${opts} set=${set} name="flac" label="Originales sin pérdida → FLAC" />
      </div>
    </details>
  </div>`;
}

function Job({ job, onCancel, onOpen }) {
  const [showLog, setShowLog] = useState(false);
  const [showItems, setShowItems] = useState(true);
  const active = job.status === "running" || job.status === "queued";
  const items = job.items;
  const pos = job.position;
  const total = pos ? pos[1] : items.length;
  // several tracks can be in progress at once: sum their progress
  const overall = total ? Math.min(100, items.reduce((sum, it) => sum + it.percent, 0) / total) : 0;
  const working = items.filter((i) => i.status === "downloading" || i.status === "processing");
  const speed = working.reduce((sum, it) => sum + (it.speed || 0), 0);
  const done = items.filter((i) => i.status === "done").length;
  const existed = items.filter((i) => i.status === "exists").length;
  const finished = done + existed;

  return html`<div class="job">
    <div class="job-head">
      <div class="name" title=${job.url}>${job.label}</div>
      <span class="status ${job.status}">${STATUS_LABEL[job.status]}</span>
    </div>
    ${job.status === "running" && html`
      <div class="bar ${!items.length ? "indet" : ""}"><i style=${`width:${overall}%`}></i></div>
      <div class="meta" style="margin-top:6px">
        ${items.length
          ? html`<span>${finished} de ${total} listas</span>`
          : html`<span>Preparando…</span>`}
        ${working.length > 1 ? html`<span>${working.length} a la vez</span>` : null}
        ${speed ? html`<span>${fmtSpeed(speed)}</span>` : null}
      </div>`}
    ${job.status !== "running" && job.status !== "queued" && html`
      <div class="meta" style="margin-top:6px">
        <span>${done || existed || job.status !== "done"
          ? `${done} archivo${done === 1 ? "" : "s"} descargado${done === 1 ? "" : "s"}`
          : "Nada nuevo: ya descargado o filtrado (ver log)"}</span>
        ${existed ? html`<span>${existed} ya existía${existed === 1 ? "" : "n"}</span>` : null}
        <span>${job.path}</span>
      </div>`}
    ${job.error && html`<div class="error-msg">${job.error}</div>`}

    ${items.length > 0 && showItems && html`<div class="items">
      ${items.map((it) => html`<div>
        <div class="item-row">
          <span class="t" title=${it.file || it.title}>${it.title}</span>
          <span class="status ${it.status === "done" ? "done" : it.status === "error" ? "error"
            : ["exists", "cancelled", "skipped", "preparing"].includes(it.status) ? "queued" : "running"}">
            ${it.status === "downloading" ? Math.round(it.percent) + "%" : STATUS_LABEL[it.status] || it.status}
          </span>
        </div>
        ${(it.status === "downloading" || it.status === "processing") &&
          html`<div class="bar"><i style=${`width:${it.percent}%`}></i></div>`}
      </div>`)}
    </div>`}

    <div class="actions" style="margin-top:10px">
      ${items.length > 0 && html`<button class="btn ghost" onClick=${() => setShowItems(!showItems)}>
        ${showItems ? "Ocultar pistas" : `Pistas (${items.length})`}</button>`}
      <button class="btn ghost" onClick=${() => setShowLog(!showLog)}>${showLog ? "Ocultar log" : "Log"}</button>
      <button class="btn ghost" onClick=${() => onOpen(job)}>Abrir carpeta</button>
      ${active && html`<button class="btn" onClick=${() => onCancel(job)}>Cancelar</button>`}
    </div>
    ${showLog && html`<div>
      <div class="cmd">${job.command}</div>
      <div class="log">${job.log.map((l) => html`<div class=${/ERROR/.test(l) ? "e" : /WARNING/.test(l) ? "w" : ""}>${l}</div>`)}</div>
    </div>`}
  </div>`;
}

function App() {
  const [config, setConfig] = useState(null);
  const [query, setQuery] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [results, setResults] = useState([]);
  const [selected, setSelected] = useState(null);
  const [mode, setMode] = useState("tracks");
  const [opts, setOpts] = useState(() => store.get("scdl-options", DEFAULT_OPTIONS));
  const [jobs, setJobs] = useState([]);
  const inputRef = useRef();

  const set = (patch) => setOpts((o) => { const n = { ...o, ...patch }; store.set("scdl-options", n); return n; });

  useEffect(() => {
    api("/api/config").then(setConfig).catch((e) => setError(e.message));
    inputRef.current && inputRef.current.focus();
    // ?q=<url or search> pre-fills and runs the search
    const q = new URLSearchParams(location.search).get("q");
    if (q) { setQuery(q); submit(null, q); }
  }, []);

  const active = jobs.some((j) => j.status === "running" || j.status === "queued");
  useEffect(() => {
    let stop = false;
    const tick = () => api("/api/jobs").then((j) => !stop && setJobs(j)).catch(() => {});
    tick();
    const t = setInterval(tick, active ? 800 : 3000);
    return () => { stop = true; clearInterval(t); };
  }, [active]);

  const submit = async (e, value) => {
    e && e.preventDefault();
    const q = (value ?? query).trim();
    if (!q) return;
    setBusy(true); setError("");
    try {
      if (isUrl(q)) {
        const info = await api(`/api/resolve?url=${encodeURIComponent(q)}`);
        setResults([]); choose(info);
      } else {
        const r = await api(`/api/search?q=${encodeURIComponent(q)}&limit=30`);
        setResults(r); setSelected(null);
        if (!r.length) setError("Sin resultados");
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const choose = (it) => {
    setSelected(it);
    setMode(it.kind === "user" ? "tracks" : "auto");
  };

  const enqueue = async (it, m) => {
    setError("");
    const modeLabel = it.kind === "user" ? ` · ${userModes(it).find(([k]) => k === m)[1]}` : "";
    try {
      await api("/api/jobs", { url: it.url, mode: m, options: opts, label: `${it.title}${modeLabel}` });
      setJobs(await api("/api/jobs"));
    } catch (err) {
      setError(err.message);
    }
  };

  const cancel = (job) => api(`/api/jobs/${job.id}/cancel`, {}).catch((e) => setError(e.message));
  const openDir = (job) => api(`/api/jobs/${job.id}/open`, {}).catch((e) => setError(e.message));
  const clear = async () => { await api("/api/jobs/clear", {}); setJobs(await api("/api/jobs")); };

  const isCollection = !selected || selected.kind !== "track";
  const running = jobs.filter((j) => j.status === "running" || j.status === "queued").length;

  return html`
    <header class="topbar">
      <div class="logo">
        <span class="logo-mark"><svg width="16" height="16" viewBox="0 0 32 32"><path d="M16 5v15m0 0-6-6m6 6 6-6M8 27h16" stroke="white" stroke-width="3.5" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg></span>
        scdl
      </div>
      <span class="muted small">${config ? `v${config.version}` : ""}</span>
      <span class="spacer"></span>
      ${running > 0 && html`<span class="small"><span class="spinner"></span> ${running} en curso</span>`}
    </header>

    <main class="layout">
      <section class="stack">
        <div class="panel">
          <form class="searchbar" onSubmit=${submit}>
            <input ref=${inputRef} type="text" value=${query} onInput=${(e) => setQuery(e.target.value)}
              placeholder="Pega una URL de SoundCloud (pista, playlist, usuario, on.soundcloud.com…) o busca" />
            <button class="btn primary" disabled=${busy}>
              ${busy ? html`<span class="spinner"></span>` : isUrl(query) ? "Abrir" : "Buscar"}
            </button>
          </form>
          ${error && html`<div class="error-msg">${error}</div>`}
          ${config && !config.ffmpeg && html`<div class="notice" style="margin-top:12px">
            No se encontró <b>ffmpeg</b> en el PATH: hace falta para convertir y etiquetar.</div>`}

          ${selected && html`<div style="margin-top:16px">
            <div class="preview">
              <${Art} src=${selected.artwork} kind=${selected.kind} />
              <div style="flex:1;min-width:0">
                <div class="title">${selected.title}</div>
                <${ItemMeta} it=${selected} />
                <div class="muted small" style="margin-top:4px;word-break:break-all">${selected.url}</div>
              </div>
            </div>
            ${selected.kind === "user" && html`<div class="chips">
              ${userModes(selected).map(([m, label, count]) => html`
                <button class="chip ${mode === m ? "on" : ""}" onClick=${() => setMode(m)}>
                  ${label}${count != null ? html`<span class="count">${fmtNum(count)}</span>` : ""}
                </button>`)}
            </div>`}
            <div class="actions">
              ${results.length > 0 && html`<button class="btn ghost" onClick=${() => setSelected(null)}>Volver a resultados</button>`}
              <button class="btn primary big" onClick=${() => enqueue(selected, mode)}>Descargar</button>
            </div>
          </div>`}

          ${!selected && results.length > 0 && html`<div class="results" style="margin-top:12px">
            ${results.map((it) => html`<div class="result" onClick=${() => choose(it)}>
              <${Art} src=${it.artwork} kind=${it.kind} size="sm" />
              <div class="info">
                <div class="name">${it.title}</div>
                <${ItemMeta} it=${it} />
              </div>
              ${it.kind !== "user" && html`<button class="btn" title="Descargar directamente"
                onClick=${(e) => { e.stopPropagation(); enqueue(it, "auto"); }}>Descargar</button>`}
            </div>`)}
          </div>`}
        </div>

        <${Options} opts=${opts} set=${set} config=${config} isCollection=${isCollection} />
      </section>

      <section>
        <div class="panel">
          <div style="display:flex;align-items:center;margin-bottom:12px">
            <h2 style="margin:0;flex:1">Descargas</h2>
            ${jobs.some((j) => !["running", "queued"].includes(j.status)) &&
              html`<button class="btn ghost" onClick=${clear}>Limpiar terminadas</button>`}
          </div>
          ${jobs.length === 0
            ? html`<div class="empty">Aún no hay descargas.<br/>Busca algo o pega una URL para empezar.</div>`
            : jobs.map((j) => html`<${Job} key=${j.id} job=${j} onCancel=${cancel} onOpen=${openDir} />`)}
        </div>
      </section>
    </main>`;
}

render(html`<${App} />`, document.getElementById("app"));

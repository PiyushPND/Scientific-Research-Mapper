import {
  memo,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type CSSProperties,
  type FormEvent,
  type KeyboardEvent,
  type PointerEvent,
  type ReactNode,
} from "react";
import "./App.css";

interface Stats {
  total_papers: number;
  maximum_capacity: number;
  remaining_capacity: number;
}
interface IngestionResult {
  status: string;
  total_received: number;
  inserted: number;
  duplicates: number;
  total_in_database: number;
  message: string;
}
interface MapNode {
  paper_id: string;
  cluster_id: number;
  membership_probability: number;
  x: number;
  y: number;
  title: string;
  abstract: string;
  authors: string | null;
  year: number | null;
  topic_id: number | null;
  topic_label: string | null;
}
interface ResearchMap {
  run_id: string | null;
  map_stale: boolean;
  nodes: MapNode[];
}
interface ManagedPaper {
  paper_id: string;
  title: string;
  abstract: string;
  authors: string | null;
  year: number | null;
  doi: string | null;
  source: string | null;
}

const API_URL = "http://localhost:8000";
const MAX_MANAGED_PAPERS = 40000;
const COLORS = [
  "#5368ce",
  "#e36b48",
  "#2a9d8f",
  "#d99a2b",
  "#9b5de5",
  "#e76f51",
];

async function requestJson<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, options);
  const data = await response.json();
  if (!response.ok)
    throw new Error(data.detail || "The backend request failed.");
  return data as T;
}

const PaperEntry = memo(function PaperEntry({
  paper,
  selected,
  onToggleSelection,
  onInspect,
  onDelete,
  onSave,
}: {
  paper: ManagedPaper;
  selected: boolean;
  onToggleSelection: (paperId: string) => void;
  onInspect: (paper: ManagedPaper) => void;
  onDelete: (paperId: string) => void;
  onSave: (paper: ManagedPaper) => Promise<boolean>;
}) {
  const [saving, setSaving] = useState(false);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(paper);
  const details = [
    paper.year?.toString(),
    paper.authors,
    paper.source,
    paper.doi,
  ].filter((detail): detail is string => Boolean(detail?.trim()));
  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    try {
      if (await onSave(draft)) setEditing(false);
    } finally {
      setSaving(false);
    }
  }
  return (
    <div className="paper-entry">
      <article className={`paper-row${selected ? " paper-row-selected" : ""}`}>
        <input
          type="checkbox"
          checked={selected}
          onChange={() => onToggleSelection(paper.paper_id)}
          aria-label={`Select ${paper.title}`}
        />
        <div className="paper-summary" onClick={() => onInspect(paper)}>
          <strong>{paper.title}</strong>
          <span>{details.join(" · ") || "No additional details"}</span>
        </div>
        {selected && (
          <>
            <button
              className="management-action-button"
              onClick={() => {
                setDraft(paper);
                setEditing(true);
              }}
            >
              Edit
            </button>
            <button
              className="management-action-button management-delete-button"
              onClick={() => onDelete(paper.paper_id)}
            >
              Delete
            </button>
          </>
        )}
      </article>
      {editing && (
        <div className="edit-form-reveal">
          <form
            className="edit-form"
            onSubmit={(event) => void handleSubmit(event)}
          >
            <h3>Edit paper</h3>
            <input
              value={draft.title}
              onChange={(event) =>
                setDraft({ ...draft, title: event.target.value })
              }
              placeholder="Title"
              required
            />
            <textarea
              value={draft.abstract}
              onChange={(event) =>
                setDraft({ ...draft, abstract: event.target.value })
              }
              placeholder="Abstract"
              required
            />
            <div className="edit-grid">
              <input
                value={draft.authors ?? ""}
                onChange={(event) =>
                  setDraft({ ...draft, authors: event.target.value || null })
                }
                placeholder="Authors"
              />
              <input
                value={draft.year ?? ""}
                onChange={(event) =>
                  setDraft({
                    ...draft,
                    year: event.target.value
                      ? Number(event.target.value)
                      : null,
                  })
                }
                type="number"
                placeholder="Year"
              />
              <input
                value={draft.source ?? ""}
                onChange={(event) =>
                  setDraft({ ...draft, source: event.target.value || null })
                }
                placeholder="Source"
              />
              <input
                value={draft.doi ?? ""}
                onChange={(event) =>
                  setDraft({ ...draft, doi: event.target.value || null })
                }
                placeholder="DOI"
              />
            </div>
            <button type="submit" disabled={saving}>
              {saving ? "Saving..." : "Save changes"}
            </button>
            <button
              type="button"
              className="secondary-button"
              onClick={() => setEditing(false)}
              disabled={saving}
            >
              Cancel
            </button>
          </form>
        </div>
      )}
    </div>
  );
});

function CollapsibleSection({
  title,
  subtitle,
  children,
  className = "",
  open: controlledOpen,
  onOpenChange,
  collapsible = true,
  style,
  resizeHandle,
}: {
  title: string;
  subtitle?: string;
  children: ReactNode;
  className?: string;
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  collapsible?: boolean;
  style?: CSSProperties;
  resizeHandle?: ReactNode;
}) {
  const [open, setOpen] = useState(true);
  const isOpen = collapsible ? (controlledOpen ?? open) : true;
  function toggle() {
    const next = !isOpen;
    if (controlledOpen === undefined) setOpen(next);
    onOpenChange?.(next);
  }
  return (
    <section className={`panel collapsible-section ${className}`} style={style}>
      {collapsible ? (
        <button
          className="section-toggle"
          onClick={toggle}
          aria-expanded={isOpen}
        >
          <span>
            <strong>{title}</strong>
            {subtitle && <small>{subtitle}</small>}
          </span>
          <i className={`chevron ${isOpen ? "chevron-up" : "chevron-down"}`} />
        </button>
      ) : (
        <div className="section-toggle section-heading">
          <span>
            <strong>{title}</strong>
            {subtitle && <small>{subtitle}</small>}
          </span>
        </div>
      )}
      <div
        className={`section-content ${collapsible ? (isOpen ? "section-content-open" : "section-content-closed") : "section-content-open section-content-static"}`}
        aria-hidden={collapsible && !isOpen}
      >
        {children}
      </div>
      {resizeHandle}
    </section>
  );
}

function App() {
  const [theme, setTheme] = useState<"light" | "dark">(() => {
    try {
      return localStorage.getItem("research-mapper-theme") === "dark"
        ? "dark"
        : "light";
    } catch {
      return "light";
    }
  });
  const [file, setFile] = useState<File | null>(null);
  const [stats, setStats] = useState<Stats | null>(null);
  const [statsLoading, setStatsLoading] = useState(true);
  const [result, setResult] = useState<IngestionResult | null>(null);
  const [researchMap, setResearchMap] = useState<ResearchMap | null>(null);
  const [selectedNode, setSelectedNode] = useState<MapNode | null>(null);
  const [paperDetailScrollRequest, setPaperDetailScrollRequest] = useState(0);
  const paperDetailRef = useRef<HTMLElement | null>(null);
  const [topicFilter, setTopicFilter] = useState<number | null>(null);
  const [mapZoom, setMapZoom] = useState(1);
  const [mapOffset, setMapOffset] = useState({ x: 0, y: 0 });
  const [isMapPanning, setIsMapPanning] = useState(false);
  const mapGroup = useRef<SVGGElement | null>(null);
  const mapPan = useRef<{
    pointerId: number;
    startX: number;
    startY: number;
    startOffset: { x: number; y: number };
    offset: { x: number; y: number };
    moved: boolean;
  } | null>(null);
  const [papers, setPapers] = useState<ManagedPaper[]>([]);
  const [paperQuery, setPaperQuery] = useState("");
  const [yearFrom, setYearFrom] = useState("");
  const [yearTo, setYearTo] = useState("");
  const [selectedPapers, setSelectedPapers] = useState<string[]>([]);
  const [error, setError] = useState("");
  const [stage, setStage] = useState("");
  const [uploadOpen, setUploadOpen] = useState(true);
  const [manageHeight, setManageHeight] = useState<number | null>(null);
  const manageResize = useRef<{
    pointerId: number;
    startY: number;
    startHeight: number;
    panel: HTMLElement;
  } | null>(null);
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    try {
      localStorage.setItem("research-mapper-theme", theme);
    } catch {
      return;
    }
  }, [theme]);
  const fetchStats = useCallback(async () => {
    setStatsLoading(true);
    try {
      setStats(await requestJson<Stats>("/api/papers/stats"));
    } catch {
      setError("Backend unavailable. Start the FastAPI server.");
    } finally {
      setStatsLoading(false);
    }
  }, []);
  async function fetchMap() {
    try {
      setResearchMap(await requestJson<ResearchMap>("/api/clustering/map"));
    } catch (error) {
      setError(
        error instanceof Error
          ? error.message
          : "Unable to load the research map.",
      );
    }
  }
  const fetchPapers = useCallback(async () => {
    const params = new URLSearchParams({ limit: String(MAX_MANAGED_PAPERS) });
    if (paperQuery.trim()) params.set("query", paperQuery.trim());
    if (yearFrom) params.set("year_from", yearFrom);
    if (yearTo) params.set("year_to", yearTo);
    const response = await requestJson<{ results: ManagedPaper[] }>(
      `/api/discovery/search?${params}`,
    );
    setPapers(response.results);
    setSelectedPapers([]);
  }, [paperQuery, yearFrom, yearTo]);
  useEffect(() => {
    void Promise.all([
      requestJson<Stats>("/api/papers/stats"),
      requestJson<ResearchMap>("/api/clustering/map"),
      requestJson<{ results: ManagedPaper[] }>(
        `/api/discovery/search?limit=${MAX_MANAGED_PAPERS}`,
      ),
    ])
      .then(([loadedStats, loadedMap, loadedPapers]) => {
        setStats(loadedStats);
        setResearchMap(loadedMap);
        setPapers(loadedPapers.results);
      })
      .catch(() => setError("Backend unavailable. Start the FastAPI server."))
      .finally(() => setStatsLoading(false));
  }, []);
  useEffect(() => {
    if (paperDetailScrollRequest > 0)
      paperDetailRef.current?.scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
  }, [paperDetailScrollRequest]);
  async function finishProcessing() {
    setStage("Preprocessing papers...");
    let preprocessing = await requestJson<{ pending_papers: number }>(
      "/api/preprocessing/run",
      { method: "POST" },
    );
    while (preprocessing.pending_papers > 0)
      preprocessing = await requestJson<{ pending_papers: number }>(
        "/api/preprocessing/run",
        { method: "POST" },
      );
    setStage("Generating paper embeddings...");
    let embeddings = await requestJson<{ pending_papers: number }>(
      "/api/embeddings/run",
      { method: "POST" },
    );
    while (embeddings.pending_papers > 0)
      embeddings = await requestJson<{ pending_papers: number }>(
        "/api/embeddings/run",
        { method: "POST" },
      );
    setStage("Clustering research papers...");
    const clustering = await requestJson<{ run_id: string }>(
      "/api/clustering/run",
      { method: "POST" },
    );
    setStage("Extracting topics...");
    await requestJson(
      `/api/topics/generate?run_id=${encodeURIComponent(clustering.run_id)}`,
      { method: "POST" },
    );
    setStage("Loading interactive map...");
    await fetchMap();
  }
  async function handleUpload() {
    if (!file) {
      setError("Please select a .csv dataset.");
      return;
    }
    setError("");
    setResult(null);
    setSelectedNode(null);
    setStage("Uploading papers...");
    const formData = new FormData();
    formData.append("file", file);
    try {
      const ingestion = await requestJson<IngestionResult>(
        "/api/ingestion/upload",
        { method: "POST", body: formData },
      );
      setResult(ingestion);
      if (ingestion.inserted > 0 || !researchMap || researchMap.map_stale)
        await finishProcessing();
      else {
        setStage("Loading existing map...");
        await fetchMap();
      }
      await fetchStats();
      await fetchPapers();
      setStage("");
    } catch (error) {
      setStage("");
      setError(
        error instanceof Error ? error.message : "Unexpected error occurred.",
      );
    }
  }
  async function handleRebuildMap() {
    setError("");
    setStage("Rebuilding map...");
    try {
      await finishProcessing();
      await fetchStats();
      setStage("");
    } catch (error) {
      setStage("");
      setError(
        error instanceof Error ? error.message : "Unable to rebuild the map.",
      );
    }
  }
  function startNewUpload() {
    setUploadOpen(true);
    setError("");
  }
  function startManageResize(event: PointerEvent<HTMLDivElement>) {
    const panel = event.currentTarget.parentElement;
    if (!(panel instanceof HTMLElement)) return;
    manageResize.current = {
      pointerId: event.pointerId,
      startY: event.clientY,
      startHeight: panel.getBoundingClientRect().height,
      panel,
    };
    event.currentTarget.setPointerCapture(event.pointerId);
  }
  function moveManageResize(event: PointerEvent<HTMLDivElement>) {
    const resize = manageResize.current;
    if (!resize || resize.pointerId !== event.pointerId) return;
    const height = Math.max(
      240,
      resize.startHeight + event.clientY - resize.startY,
    );
    resize.panel.style.height = `${height}px`;
    resize.panel.style.flex = "0 0 auto";
  }
  function finishManageResize(event: PointerEvent<HTMLDivElement>) {
    const resize = manageResize.current;
    if (!resize || resize.pointerId !== event.pointerId) return;
    setManageHeight(resize.panel.getBoundingClientRect().height);
    manageResize.current = null;
  }
  function handleManageResizeKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key !== "ArrowUp" && event.key !== "ArrowDown") return;
    event.preventDefault();
    const panel = event.currentTarget.parentElement;
    if (!(panel instanceof HTMLElement)) return;
    const currentHeight = manageHeight ?? panel.getBoundingClientRect().height;
    setManageHeight(
      Math.max(240, currentHeight + (event.key === "ArrowDown" ? 24 : -24)),
    );
  }
  const togglePaperSelection = useCallback((paperId: string) => {
    setSelectedPapers((current) =>
      current.includes(paperId)
        ? current.filter((id) => id !== paperId)
        : [...current, paperId],
    );
  }, []);
  const handleDelete = useCallback(
    async (paperIds: string[]) => {
      if (
        !paperIds.length ||
        !window.confirm(
          `Delete ${paperIds.length} selected paper${paperIds.length === 1 ? "" : "s"}?`,
        )
      )
        return;
      try {
        await requestJson("/api/papers/bulk-delete", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ paper_ids: paperIds }),
        });
        setSelectedNode(null);
        setResearchMap((current) =>
          current ? { ...current, map_stale: true, nodes: [] } : current,
        );
        await fetchStats();
        await fetchPapers();
      } catch (error) {
        setError(
          error instanceof Error ? error.message : "Unable to delete papers.",
        );
      }
    },
    [fetchStats, fetchPapers],
  );
  const deletePaper = useCallback(
    (paperId: string) => {
      void handleDelete([paperId]);
    },
    [handleDelete],
  );
  const inspectPaper = useCallback(
    (paper: ManagedPaper) =>
      setSelectedNode({
        ...paper,
        cluster_id: -1,
        membership_probability: 0,
        x: 0,
        y: 0,
        topic_id: null,
        topic_label: null,
      }),
    [],
  );
  const savePaper = useCallback(
    async (paper: ManagedPaper): Promise<boolean> => {
      try {
        const updated = await requestJson<ManagedPaper>(
          `/api/papers/${encodeURIComponent(paper.paper_id)}`,
          {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(paper),
          },
        );
        setPapers((current) =>
          current.map((currentPaper) =>
            currentPaper.paper_id === updated.paper_id ? updated : currentPaper,
          ),
        );
        setResearchMap((current) =>
          current ? { ...current, map_stale: true } : current,
        );
        return true;
      } catch (error) {
        setError(
          error instanceof Error
            ? error.message
            : "Unable to update the paper.",
        );
        return false;
      }
    },
    [],
  );

  const percentage = stats
    ? Math.min((stats.total_papers / stats.maximum_capacity) * 100, 100)
    : 0;
  const nodes = useMemo(() => researchMap?.nodes ?? [], [researchMap]);
  const bounds = useMemo(() => {
    if (!nodes.length) return { minX: 0, maxX: 1, minY: 0, maxY: 1 };
    return {
      minX: Math.min(...nodes.map((node) => node.x)),
      maxX: Math.max(...nodes.map((node) => node.x)),
      minY: Math.min(...nodes.map((node) => node.y)),
      maxY: Math.max(...nodes.map((node) => node.y)),
    };
  }, [nodes]);
  const topics = useMemo(() => {
    const summaries = new Map<number, { label: string; count: number }>();
    for (const node of nodes) {
      const current = summaries.get(node.cluster_id);
      if (current) current.count++;
      else
        summaries.set(node.cluster_id, {
          label: node.topic_label ?? "Noise",
          count: 1,
        });
    }
    return [...summaries.entries()]
      .map(([cluster, summary]) => ({ cluster, ...summary }))
      .sort((a, b) =>
        a.label === "Noise"
          ? 1
          : b.label === "Noise"
            ? -1
            : a.label.localeCompare(b.label),
      );
  }, [nodes]);
  const visibleNodes =
    topicFilter === null
      ? nodes
      : nodes.filter((node) => node.cluster_id === topicFilter);
  const allPapersSelected =
    papers.length > 0 && selectedPapers.length === papers.length;
  const position = (node: MapNode) => ({
    x: 35 + ((node.x - bounds.minX) / (bounds.maxX - bounds.minX || 1)) * 830,
    y: 35 + ((bounds.maxY - node.y) / (bounds.maxY - bounds.minY || 1)) * 450,
  });
  function selectMapNode(node: MapNode) {
    setSelectedNode(node);
    setPaperDetailScrollRequest((request) => request + 1);
  }
  const mapTransform = (zoom: number, offset: { x: number; y: number }) =>
    `translate(${offset.x} ${offset.y}) translate(450 260) scale(${zoom}) translate(-450 -260)`;
  function getMapPoint(event: PointerEvent<SVGSVGElement>) {
    const matrix = event.currentTarget.getScreenCTM();
    if (!matrix) return null;
    return new DOMPoint(event.clientX, event.clientY).matrixTransform(
      matrix.inverse(),
    );
  }
  function startMapPan(event: PointerEvent<SVGSVGElement>) {
    if (event.button !== 0) return;
    const point = getMapPoint(event);
    if (!point) return;
    mapPan.current = {
      pointerId: event.pointerId,
      startX: point.x,
      startY: point.y,
      startOffset: mapOffset,
      offset: mapOffset,
      moved: false,
    };
  }
  function moveMapPan(event: PointerEvent<SVGSVGElement>) {
    const pan = mapPan.current;
    if (!pan || pan.pointerId !== event.pointerId) return;
    const point = getMapPoint(event);
    if (!point) return;
    const x = point.x - pan.startX;
    const y = point.y - pan.startY;
    if (!pan.moved) {
      if (Math.hypot(x, y) < 2) return;
      pan.moved = true;
      event.currentTarget.setPointerCapture(event.pointerId);
      setIsMapPanning(true);
    }
    pan.offset = { x: pan.startOffset.x + x, y: pan.startOffset.y + y };
    mapGroup.current?.setAttribute(
      "transform",
      mapTransform(mapZoom, pan.offset),
    );
  }
  function finishMapPan(event: PointerEvent<SVGSVGElement>) {
    const pan = mapPan.current;
    if (!pan || pan.pointerId !== event.pointerId) return;
    if (pan.moved) setMapOffset(pan.offset);
    pan.pointerId = -1;
    setIsMapPanning(false);
  }

  return (
    <main className="dashboard">
      <header className="header">
        <div>
          <span className="eyebrow">
            MACHINE LEARNING AND NATURAL LANGUAGE PROCESSING
          </span>
          <h1>Scientific Research Mapper</h1>
          <p>
            Upload a research dataset and explore its discovered topics on an
            interactive map.
          </p>
        </div>
        <div className="header-tools">
          <div className="theme-setting">
            <button
              className="theme-toggle"
              onClick={() =>
                setTheme((current) => (current === "light" ? "dark" : "light"))
              }
              aria-label={`Switch to ${theme === "light" ? "dark" : "light"} theme`}
              title={`Switch to ${theme === "light" ? "dark" : "light"} theme`}
            >
              <span className="theme-icon" aria-hidden="true">
                {theme === "light" ? "☾" : "☀"}
              </span>
            </button>
            <span className="theme-caption">
              {theme === "light" ? "Light mode" : "Dark mode"}
            </span>
          </div>
          <div className="capacity-circle">
            <svg
              viewBox="0 0 80 80"
              aria-label={`${percentage.toFixed(2)} percent capacity used`}
              role="img"
            >
              <circle className="capacity-track" cx="40" cy="40" r="32" />
              <circle
                className="capacity-value"
                cx="40"
                cy="40"
                r="32"
                style={{
                  strokeDashoffset: `${201.06 - (percentage / 100) * 201.06}`,
                }}
              />
              <text x="40" y="43">
                {percentage.toFixed(2)}%
              </text>
            </svg>
            <span>Capacity</span>
          </div>
        </div>
      </header>

      <div className="upload-anchor">
        <CollapsibleSection
          title="Upload research papers"
          className="upload-section"
          open={uploadOpen}
          onOpenChange={setUploadOpen}
        >
          <p>
            Upload a <strong>.csv</strong> file only. It must include{" "}
            <strong>title</strong> and <strong>abstract</strong> columns for
            each paper.
          </p>
          <div className="upload-area">
            <label className="upload-dropzone">
              <input
                type="file"
                accept=".csv,text/csv"
                onChange={(event) => {
                  setFile(event.target.files?.[0] ?? null);
                  setResult(null);
                  setError("");
                }}
              />
              <span className="upload-icon">↑</span>
              <strong>
                {file ? file.name : "Upload a .csv dataset of research papers"}
              </strong>
              <small>.csv file only, required columns: title, abstract</small>
            </label>
          </div>
          {file && (
            <button
              onClick={() => void handleUpload()}
              disabled={Boolean(stage)}
            >
              {stage || "Upload and build map"}
            </button>
          )}
          {error && <div className="error">{error}</div>}
          {result && (
            <div className="result">
              <h3>Research map updated</h3>
              <p>{result.message}</p>
              <div className="result-grid">
                <div>
                  <strong>{result.total_received}</strong>
                  <span>Received</span>
                </div>
                <div>
                  <strong>{result.inserted}</strong>
                  <span>Inserted</span>
                </div>
                <div>
                  <strong>{result.duplicates}</strong>
                  <span>Duplicates</span>
                </div>
                <div>
                  <strong>{result.total_in_database}</strong>
                  <span>Total stored</span>
                </div>
              </div>
            </div>
          )}
        </CollapsibleSection>
      </div>

      <div className="map-anchor">
        <CollapsibleSection
          title="Interactive research map"
          className="map-section"
          collapsible={false}
        >
          <div className="map-heading">
            <p>
              {nodes.length
                ? "Drag to pan, zoom in or out, or select a point to inspect a paper. Choose a topic to filter; select it again to show all."
                : "No papers are currently mapped."}
            </p>
            <div className="manage-actions">
              {researchMap?.map_stale && (
                <button
                  className="secondary-button"
                  onClick={() => void handleRebuildMap()}
                  disabled={Boolean(stage)}
                >
                  Rebuild map
                </button>
              )}
              <button
                className="secondary-button upload-another-button"
                onClick={startNewUpload}
              >
                Upload another .csv dataset
              </button>
            </div>
          </div>
          <div className="map-toolbar">
            <div className="map-zoom-controls" aria-label="Map zoom controls">
              <button
                className="secondary-button"
                onClick={() => setMapZoom((zoom) => Math.min(4, zoom + 0.25))}
                disabled={!nodes.length || mapZoom >= 4}
                aria-label="Zoom in"
                title="Zoom in"
              >
                <svg aria-hidden="true" viewBox="0 0 24 24">
                  <circle cx="10.8" cy="10.8" r="6.8" />
                  <path d="M16 16l5 5M10.8 7.5v6.6M7.5 10.8h6.6" />
                </svg>
              </button>
              <span>{Math.round(mapZoom * 100)}%</span>
              <button
                className="secondary-button"
                onClick={() => setMapZoom((zoom) => Math.max(1, zoom - 0.25))}
                disabled={!nodes.length || mapZoom <= 1}
                aria-label="Zoom out"
                title="Zoom out"
              >
                <svg aria-hidden="true" viewBox="0 0 24 24">
                  <circle cx="10.8" cy="10.8" r="6.8" />
                  <path d="M16 16l5 5M7.5 10.8h6.6" />
                </svg>
              </button>
              <button
                className="secondary-button"
                onClick={() => {
                  setMapZoom(1);
                  setMapOffset({ x: 0, y: 0 });
                }}
                disabled={
                  !nodes.length ||
                  (mapZoom === 1 && mapOffset.x === 0 && mapOffset.y === 0)
                }
                aria-label="Reset zoom"
                title="Reset zoom"
              >
                <svg aria-hidden="true" viewBox="0 0 24 24">
                  <path d="M3 11a9 9 0 1 1 2.64 6.36L3 15.5" />
                  <path d="M3 20v-4.5h4.5" />
                </svg>
                Reset Zoom
              </button>
            </div>
            <span className="map-result-count">
              {visibleNodes.length.toLocaleString()} papers
            </span>
          </div>
          <div className="map-container">
            <svg
              className={`map-svg${isMapPanning ? " map-panning" : ""}`}
              viewBox="0 0 900 520"
              role={nodes.length ? "group" : "img"}
              aria-label={
                nodes.length
                  ? "Interactive research paper map"
                  : "Research map. Upload a CSV dataset to populate the map."
              }
              onPointerDown={startMapPan}
              onPointerMove={moveMapPan}
              onPointerUp={finishMapPan}
              onPointerCancel={finishMapPan}
            >
              <rect
                width="900"
                height="520"
                rx="12"
                className="map-background"
              />
              {nodes.length === 0 ? (
                <text x="450" y="260" className="map-empty-text">
                  Map points will appear here when map data is available.
                </text>
              ) : (
                <g ref={mapGroup} transform={mapTransform(mapZoom, mapOffset)}>
                  {visibleNodes.map((node) => {
                    const point = position(node);
                    return (
                      <circle
                        key={node.paper_id}
                        cx={point.x}
                        cy={point.y}
                        r={selectedNode?.paper_id === node.paper_id ? 9 : 6}
                        fill={
                          node.cluster_id < 0
                            ? "#9aa3b5"
                            : COLORS[node.cluster_id % COLORS.length]
                        }
                        className="map-node"
                        onClick={(event) => {
                          if (mapPan.current?.moved && event.detail !== 0)
                            return;
                          selectMapNode(node);
                        }}
                        onKeyDown={(event) => {
                          if (event.key === "Enter" || event.key === " ") {
                            event.preventDefault();
                            selectMapNode(node);
                          }
                        }}
                        role="button"
                        aria-label={`View paper: ${node.title}`}
                        tabIndex={0}
                      >
                        <title>{node.title}</title>
                      </circle>
                    );
                  })}
                </g>
              )}
            </svg>
          </div>
          <section className="map-topics" aria-label="Map topics">
            <h3>Topics discovered with LDA</h3>
            <p className="topic-method-note">
              {topics.length
                ? "Each cluster is described by its most informative words from a scikit-learn Latent Dirichlet Allocation model fitted to that cluster’s paper titles and abstracts."
                : "Topic labels will appear here when map data is available."}
            </p>
            <div className="map-topic-list">
              {topics.map((topic) => (
                <button
                  key={topic.cluster}
                  className="map-topic"
                  aria-pressed={topicFilter === topic.cluster}
                  onClick={() => {
                    const nextFilter =
                      topicFilter === topic.cluster ? null : topic.cluster;
                    setTopicFilter(nextFilter);
                    if (
                      nextFilter !== null &&
                      selectedNode?.cluster_id !== nextFilter
                    )
                      setSelectedNode(null);
                  }}
                >
                  <span>
                    <i
                      style={{
                        backgroundColor:
                          topic.cluster < 0
                            ? "#9aa3b5"
                            : COLORS[topic.cluster % COLORS.length],
                      }}
                    />
                    {topic.label}
                  </span>
                  <small>{topic.count.toLocaleString()}</small>
                </button>
              ))}
            </div>
          </section>
          {selectedNode && (
            <article ref={paperDetailRef} className="paper-detail">
              <button
                className="close-button"
                onClick={() => setSelectedNode(null)}
                aria-label="Close paper details"
              >
                ×
              </button>
              <span className="detail-label">
                {selectedNode.topic_label ?? "Noise"} ·{" "}
                {selectedNode.year ?? "Year unavailable"}
              </span>
              <h3>{selectedNode.title}</h3>
              <p>{selectedNode.abstract}</p>
              {selectedNode.authors && (
                <small>Authors: {selectedNode.authors}</small>
              )}
            </article>
          )}
        </CollapsibleSection>
      </div>

      <div className="side-column">
        <div className="stats-anchor">
          <CollapsibleSection
            title="Stored papers statistics"
            className="stats-section"
            collapsible={false}
          >
            <div className="stats-grid">
              <article className="stat-card">
                <span>Stored papers</span>
                <strong>
                  {statsLoading ? (
                    <span
                      className="loading-indicator"
                      role="status"
                      aria-label="Loading stored papers"
                    />
                  ) : (
                    (stats?.total_papers.toLocaleString() ?? "Unavailable")
                  )}
                </strong>
              </article>
              <article className="stat-card">
                <span>Maximum capacity</span>
                <strong>
                  {statsLoading ? (
                    <span
                      className="loading-indicator"
                      role="status"
                      aria-label="Loading maximum capacity"
                    />
                  ) : (
                    (stats?.maximum_capacity.toLocaleString() ?? "Unavailable")
                  )}
                </strong>
              </article>
              <article className="stat-card">
                <span>Remaining capacity</span>
                <strong>
                  {statsLoading ? (
                    <span
                      className="loading-indicator"
                      role="status"
                      aria-label="Loading remaining capacity"
                    />
                  ) : (
                    (stats?.remaining_capacity.toLocaleString() ??
                    "Unavailable")
                  )}
                </strong>
              </article>
            </div>
          </CollapsibleSection>
        </div>

        <CollapsibleSection
          title="Manage stored papers"
          subtitle="Search, filter, inspect, edit, or remove papers."
          className="manage-section"
          collapsible={false}
          style={
            manageHeight === null
              ? undefined
              : { height: manageHeight, flex: "0 0 auto" }
          }
          resizeHandle={
            <div
              className="manage-resize-handle"
              role="separator"
              aria-label="Resize Manage section"
              aria-orientation="horizontal"
              tabIndex={0}
              onPointerDown={startManageResize}
              onPointerMove={moveManageResize}
              onPointerUp={finishManageResize}
              onPointerCancel={finishManageResize}
              onKeyDown={handleManageResizeKeyDown}
            />
          }
        >
          <div className="paper-filters">
            <input
              value={paperQuery}
              onChange={(event) => setPaperQuery(event.target.value)}
              placeholder="Search title/abstract"
            />
            <input
              value={yearFrom}
              onChange={(event) => setYearFrom(event.target.value)}
              type="number"
              placeholder="From year"
            />
            <input
              value={yearTo}
              onChange={(event) => setYearTo(event.target.value)}
              type="number"
              placeholder="To year"
            />
            <button
              onClick={() => void fetchPapers()}
              disabled={Boolean(stage)}
            >
              Search
            </button>
          </div>
          <div className="select-actions">
            <label className="select-all select-all-row">
              <input
                type="checkbox"
                checked={allPapersSelected}
                onChange={(event) =>
                  setSelectedPapers(
                    event.target.checked
                      ? papers.map((paper) => paper.paper_id)
                      : [],
                  )
                }
                disabled={!papers.length || Boolean(stage)}
              />
              <span>Select all papers</span>
            </label>
            {selectedPapers.length > 0 && (
              <button
                className="delete-selected"
                onClick={() => void handleDelete(selectedPapers)}
                disabled={Boolean(stage)}
              >
                Delete selected ({selectedPapers.length})
              </button>
            )}
          </div>
          <div className="paper-list">
            {papers.map((paper) => (
              <PaperEntry
                key={paper.paper_id}
                paper={paper}
                selected={selectedPapers.includes(paper.paper_id)}
                onToggleSelection={togglePaperSelection}
                onInspect={inspectPaper}
                onDelete={deletePaper}
                onSave={savePaper}
              />
            ))}
            {!papers.length && (
              <p className="empty-state">
                No papers match the current filters.
              </p>
            )}
          </div>
        </CollapsibleSection>
      </div>
      {error && <div className="error">{error}</div>}
      <footer>Scientific Research Mapper · Research topics with LDA</footer>
    </main>
  );
}
export default App;

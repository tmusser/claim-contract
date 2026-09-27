import { useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";
import { parseClaimUiBundle } from "./bundle";
import { edgePath, layoutClaimGraph, nodeHeight, nodeWidth } from "./layout";
import type {
  ClaimGraphEdge,
  ClaimNode,
  DataSource,
  SourceFile,
} from "./types";

const bundleUrl =
  import.meta.env.VITE_CLAIM_BUNDLE_URL ?? "/claim-map.json";

const statusOrder = [
  "OPEN",
  "SUPPORT_MET",
  "REFUTE_MET",
  "INCONCLUSIVE",
  "RETIRED",
];

type ProvenanceFilter = "ALL" | "FILES" | "DATA" | "MISSING";

function App() {
  const [bundle, setBundle] = useState<ClaimUiBundle | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [loadAttempt, setLoadAttempt] = useState(0);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("ALL");
  const [provenance, setProvenance] = useState<ProvenanceFilter>("ALL");

  useEffect(() => {
    const controller = new AbortController();
    setLoadError(null);
    setBundle(null);

    fetch(bundleUrl, {
      signal: controller.signal,
      headers: { Accept: "application/json" },
    })
      .then(async (response) => {
        if (!response.ok) {
          throw new Error(
            `Could not load ${bundleUrl} (HTTP ${response.status}). Run claim-contract ui export first.`,
          );
        }

        let raw: unknown;
        try {
          raw = await response.json();
        } catch {
          throw new Error(
            `Could not parse ${bundleUrl} as JSON. Re-export the claim map bundle.`,
          );
        }

        return parseClaimUiBundle(raw);
      })
      .then((payload) => {
        setBundle(payload);
        setSelectedId(payload.claims[0]?.id ?? null);
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        setLoadError(error instanceof Error ? error.message : String(error));
      });

    return () => {
      controller.abort();
    };
  }, [loadAttempt]);

  const visibleClaims = useMemo(() => {
    if (!bundle) return [];
    const needle = query.trim().toLowerCase();

    return bundle.claims.filter((claim) => {
      const statusMatch = status === "ALL" || claim.status === status;
      const provenanceMatch =
        provenance === "ALL" ||
        (provenance === "FILES" && claim.source_files.length > 0) ||
        (provenance === "DATA" && claim.data_sources.length > 0) ||
        (provenance === "MISSING" &&
          claim.source_files.length === 0 &&
          claim.data_sources.length === 0);

      if (!statusMatch || !provenanceMatch) {
        return false;
      }

      if (!needle) {
        return true;
      }

      return claimSearchText(claim).includes(needle);
    });
  }, [bundle, provenance, query, status]);

  const visibleIds = useMemo(
    () => new Set(visibleClaims.map((claim) => claim.id)),
    [visibleClaims],
  );

  const visibleEdges = useMemo(() => {
    if (!bundle) return [];
    return bundle.graph.edges.filter(
      (edge) => visibleIds.has(edge.from) && visibleIds.has(edge.to),
    );
  }, [bundle, visibleIds]);

  const selectedClaim =
    selectedId && visibleIds.has(selectedId)
      ? bundle?.claims.find((claim) => claim.id === selectedId) ?? null
      : null;

  useEffect(() => {
    if (
      visibleClaims.length > 0 &&
      (!selectedId || !visibleIds.has(selectedId))
    ) {
      setSelectedId(visibleClaims[0].id);
    }
  }, [visibleClaims, visibleIds, selectedId]);

  const clearFilters = () => {
    setQuery("");
    setStatus("ALL");
    setProvenance("ALL");
  };

  const navigateToClaim = (claimId: string) => {
    clearFilters();
    setSelectedId(claimId);
  };

  if (loadError) {
    return (
      <EmptyState
        error={loadError}
        onRetry={() => setLoadAttempt((attempt) => attempt + 1)}
      />
    );
  }

  if (!bundle) {
    return (
      <main className="loading-shell">
        <div className="loading-pulse" />
        <p>Loading claim map…</p>
      </main>
    );
  }

  const statuses = statusOrder.filter((candidate) =>
    bundle.claims.some((claim) => claim.status === candidate),
  );
  const activeFilterCount =
    Number(query.trim().length > 0) +
    Number(status !== "ALL") +
    Number(provenance !== "ALL");

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <div className="eyebrow">claim-contract / optional UI</div>
          <div className="brand-row">
            <h1>Claim map</h1>
            <span className="read-only-pill">read only</span>
          </div>
          <p className="topbar-copy">
            Trace claim relationships, repository sources, logged time, and declared
            database/query lineage without changing ledger or graph state.
          </p>
        </div>

        <div className="topbar-stats" aria-label="Claim map counts">
          <Metric value={bundle.claims.length} label="claims" />
          <Metric value={bundle.graph.edges.length} label="edges" />
          <Metric value={bundle.graph.roots.length} label="roots" />
        </div>
      </header>

      <div className="boundary-banner">
        <span className="boundary-dot" />
        <div>
          <strong>Interpretation boundary.</strong> {bundle.scope_notice}
        </div>
      </div>

      <section className="toolbar">
        <label className="search-field">
          <span>Search claims and provenance</span>
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Claim ID, wording, file, table, or query ref…"
          />
        </label>

        <div className="toolbar-filters">
          <FilterGroup label="Status">
            <FilterButton
              active={status === "ALL"}
              onClick={() => setStatus("ALL")}
            >
              All
            </FilterButton>
            {statuses.map((candidate) => (
              <FilterButton
                key={candidate}
                active={status === candidate}
                onClick={() => setStatus(candidate)}
              >
                {humanize(candidate)}
              </FilterButton>
            ))}
          </FilterGroup>

          <FilterGroup label="Provenance">
            <FilterButton
              active={provenance === "ALL"}
              onClick={() => setProvenance("ALL")}
            >
              Any
            </FilterButton>
            <FilterButton
              active={provenance === "FILES"}
              onClick={() => setProvenance("FILES")}
            >
              Files
            </FilterButton>
            <FilterButton
              active={provenance === "DATA"}
              onClick={() => setProvenance("DATA")}
            >
              Data
            </FilterButton>
            <FilterButton
              active={provenance === "MISSING"}
              onClick={() => setProvenance("MISSING")}
            >
              Missing
            </FilterButton>
          </FilterGroup>
        </div>

        <div className="toolbar-summary" aria-live="polite">
          <span>
            <strong>{visibleClaims.length}</strong> of {bundle.claims.length} claims
          </span>
          {activeFilterCount > 0 ? (
            <button className="clear-button" onClick={clearFilters}>
              Clear {activeFilterCount} filter{activeFilterCount === 1 ? "" : "s"}
            </button>
          ) : null}
        </div>
      </section>

      <section className="workspace">
        <ClaimGraph
          claims={visibleClaims}
          edges={visibleEdges}
          roots={bundle.graph.roots}
          selectedId={selectedId}
          onSelect={setSelectedId}
          onClearFilters={clearFilters}
        />
        <ClaimInspector
          claim={selectedClaim}
          edges={bundle.graph.edges}
          onNavigateClaim={navigateToClaim}
        />
      </section>

      <footer className="footer">
        <span>
          Source bundle: <code>{bundle.generated_from.ledger}</code> +{" "}
          <code>{bundle.generated_from.graph}</code>
          {bundle.generated_from.provenance ? (
            <>
              {" "}
              + <code>{bundle.generated_from.provenance}</code>
            </>
          ) : null}
        </span>
        <span>scientific validation: false · automatic adjudication: false</span>
      </footer>
    </main>
  );
}

function ClaimGraph({
  claims,
  edges,
  roots,
  selectedId,
  onSelect,
  onClearFilters,
}: {
  claims: ClaimNode[];
  edges: ClaimGraphEdge[];
  roots: string[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  onClearFilters: () => void;
}) {
  const viewportRef = useRef<HTMLDivElement | null>(null);
  const [zoom, setZoom] = useState(1);

  const layout = useMemo(
    () => layoutClaimGraph(claims, edges, roots),
    [claims, edges, roots],
  );

  const relatedIds = useMemo(() => {
    const related = new Set<string>();
    if (!selectedId) return related;
    for (const edge of edges) {
      if (edge.from === selectedId) related.add(edge.to);
      if (edge.to === selectedId) related.add(edge.from);
    }
    return related;
  }, [edges, selectedId]);

  const zoomTo = (next: number) => {
    setZoom(clamp(next, 0.55, 1.45));
  };

  const fitGraph = () => {
    const viewport = viewportRef.current;
    if (!viewport) return;
    const availableWidth = Math.max(viewport.clientWidth - 48, 200);
    const availableHeight = Math.max(viewport.clientHeight - 48, 200);
    zoomTo(
      Math.min(
        availableWidth / Math.max(layout.width, 1),
        availableHeight / Math.max(layout.height, 1),
        1.2,
      ),
    );
    viewport.scrollTo({ left: 0, top: 0, behavior: "smooth" });
  };

  const centerSelected = () => {
    if (!selectedId) return;
    const viewport = viewportRef.current;
    const position = layout.positions[selectedId];
    if (!viewport || !position) return;

    const centerX = (position.x + nodeWidth / 2) * zoom;
    const centerY = (position.y + nodeHeight / 2) * zoom;
    viewport.scrollTo({
      left: Math.max(0, centerX - viewport.clientWidth / 2),
      top: Math.max(0, centerY - viewport.clientHeight / 2),
      behavior: "smooth",
    });
  };

  useEffect(() => {
    if (!selectedId) return;
    const viewport = viewportRef.current;
    const position = layout.positions[selectedId];
    if (!viewport || !position) return;

    const left = position.x * zoom;
    const right = (position.x + nodeWidth) * zoom;
    const top = position.y * zoom;
    const bottom = (position.y + nodeHeight) * zoom;
    const margin = 36;

    const outside =
      left < viewport.scrollLeft + margin ||
      right > viewport.scrollLeft + viewport.clientWidth - margin ||
      top < viewport.scrollTop + margin ||
      bottom > viewport.scrollTop + viewport.clientHeight - margin;

    if (outside) {
      const centerX = (position.x + nodeWidth / 2) * zoom;
      const centerY = (position.y + nodeHeight / 2) * zoom;
      viewport.scrollTo({
        left: Math.max(0, centerX - viewport.clientWidth / 2),
        top: Math.max(0, centerY - viewport.clientHeight / 2),
        behavior: "smooth",
      });
    }
  }, [layout.positions, selectedId, zoom]);

  if (claims.length === 0) {
    return (
      <div className="graph-panel graph-empty">
        <div className="empty-graph-card">
          <span className="panel-kicker">No matches</span>
          <h2>No claims match the current view.</h2>
          <p>Clear the filters to return to the full claim graph.</p>
          <button className="primary-button" onClick={onClearFilters}>
            Show all claims
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="graph-panel">
      <div className="graph-panel-heading">
        <div>
          <span className="panel-kicker">Declared relevance</span>
          <h2>Claim graph</h2>
        </div>

        <div className="graph-heading-actions">
          <div className="graph-legend">
            <span><i className="legend-dot root" /> root</span>
            <span><i className="legend-dot open" /> open</span>
            <span><i className="legend-dot retired" /> retired</span>
          </div>
          <div className="graph-controls" aria-label="Graph view controls">
            <button
              className="icon-button"
              onClick={() => zoomTo(zoom - 0.1)}
              aria-label="Zoom out"
              title="Zoom out"
            >
              −
            </button>
            <span className="zoom-label">{Math.round(zoom * 100)}%</span>
            <button
              className="icon-button"
              onClick={() => zoomTo(zoom + 0.1)}
              aria-label="Zoom in"
              title="Zoom in"
            >
              +
            </button>
            <button className="view-button" onClick={fitGraph}>
              Fit
            </button>
            <button
              className="view-button"
              onClick={centerSelected}
              disabled={!selectedId}
            >
              Center
            </button>
          </div>
        </div>
      </div>

      <div className="graph-scroll" ref={viewportRef}>
        <div
          className="graph-stage"
          style={{
            width: layout.width * zoom,
            height: layout.height * zoom,
          }}
        >
          <div
            className="graph-canvas"
            style={{
              width: layout.width,
              height: layout.height,
              transform: `scale(${zoom})`,
            }}
          >
            <svg
              className="edge-layer"
              width={layout.width}
              height={layout.height}
              aria-hidden="true"
            >
              <defs>
                <marker
                  id="arrow"
                  markerWidth="8"
                  markerHeight="8"
                  refX="7"
                  refY="4"
                  orient="auto"
                  markerUnits="strokeWidth"
                >
                  <path d="M0,0 L8,4 L0,8 z" className="arrow-head" />
                </marker>
                <marker
                  id="arrow-active"
                  markerWidth="8"
                  markerHeight="8"
                  refX="7"
                  refY="4"
                  orient="auto"
                  markerUnits="strokeWidth"
                >
                  <path d="M0,0 L8,4 L0,8 z" className="arrow-head-active" />
                </marker>
              </defs>

              {edges.map((edge) => {
                const source = layout.positions[edge.from];
                const target = layout.positions[edge.to];
                if (!source || !target) return null;
                const active =
                  selectedId === edge.from || selectedId === edge.to;

                return (
                  <path
                    key={`${edge.from}->${edge.to}`}
                    d={edgePath(source, target)}
                    className={active ? "graph-edge active" : "graph-edge"}
                    markerEnd={active ? "url(#arrow-active)" : "url(#arrow)"}
                  >
                    <title>{edge.rationale}</title>
                  </path>
                );
              })}
            </svg>

            {claims.map((claim) => {
              const position = layout.positions[claim.id];
              if (!position) return null;

              const selected = selectedId === claim.id;
              const related = relatedIds.has(claim.id);
              const dimmed =
                selectedId !== null &&
                relatedIds.size > 0 &&
                !selected &&
                !related;

              return (
                <button
                  key={claim.id}
                  data-claim-id={claim.id}
                  className={[
                    "claim-node",
                    claim.is_root ? "root-node" : "",
                    claim.status === "RETIRED" ? "retired-node" : "",
                    selected ? "selected" : "",
                    related ? "related" : "",
                    dimmed ? "dimmed" : "",
                  ]
                    .filter(Boolean)
                    .join(" ")}
                  style={{
                    left: position.x,
                    top: position.y,
                    width: nodeWidth,
                    height: nodeHeight,
                  }}
                  onClick={() => onSelect(claim.id)}
                  aria-pressed={selected}
                  aria-label={`Select ${claim.id}: ${claim.claim}`}
                >
                  <div className="node-topline">
                    <span className="node-id">{claim.id}</span>
                    <span
                      className={`status-dot status-${claim.status.toLowerCase()}`}
                    />
                  </div>
                  <div className="node-claim">{claim.claim}</div>
                  <div className="node-meta">
                    <span>{humanize(claim.status)}</span>
                    <span>·</span>
                    <span>{claim.source_files.length} refs</span>
                    {claim.data_sources.length > 0 ? (
                      <>
                        <span>·</span>
                        <span>{claim.data_sources.length} data</span>
                      </>
                    ) : null}
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}

function ClaimInspector({
  claim,
  edges,
  onNavigateClaim,
}: {
  claim: ClaimNode | null;
  edges: ClaimGraphEdge[];
  onNavigateClaim: (id: string) => void;
}) {
  if (!claim) {
    return (
      <aside className="inspector empty-inspector">
        <p>Select a claim to inspect its provenance.</p>
      </aside>
    );
  }

  const relationships = edges.filter(
    (edge) => edge.from === claim.id || edge.to === claim.id,
  );

  return (
    <aside className="inspector">
      <div className="inspector-header">
        <div>
          <div className="eyebrow">selected claim</div>
          <div className="inspector-title-row">
            <h2>{claim.id}</h2>
            <span className={`status-pill status-pill-${claim.status.toLowerCase()}`}>
              {humanize(claim.status)}
            </span>
          </div>
        </div>
        {claim.is_root ? <span className="root-badge">root</span> : null}
      </div>

      <section className="detail-section claim-section">
        <div className="section-heading-row">
          <h3>Claim</h3>
          <CopyButton value={claim.claim} label="Copy claim" compact />
        </div>
        <p className="claim-full">{claim.claim}</p>
      </section>

      <div className="detail-grid">
        <DetailCell label="Logged" value={formatDate(claim.logged_at)} />
        <DetailCell
          label="Generated"
          value={claim.generated_at ? formatDate(claim.generated_at) : "unknown"}
        />
        <DetailCell label="Graph" value={humanize(claim.classification)} />
        <DetailCell
          label="Last judged"
          value={
            typeof claim.judgment.last_evaluated === "string"
              ? formatDate(claim.judgment.last_evaluated)
              : "not yet"
          }
        />
      </div>

      <section className="provenance-summary">
        <ProvenanceMetric
          value={claim.source_files.length}
          label="source files"
          tone={claim.source_files.length > 0 ? "present" : "missing"}
        />
        <ProvenanceMetric
          value={claim.data_sources.length}
          label="data sources"
          tone={claim.data_sources.length > 0 ? "present" : "neutral"}
        />
        <ProvenanceMetric
          value={relationships.length}
          label="relationships"
          tone={relationships.length > 0 ? "present" : "neutral"}
        />
      </section>

      <details className="detail-disclosure" open>
        <summary>Analytical context</summary>
        <div className="disclosure-body">
          <div className="compact-detail">
            <span>Scope</span>
            <p>{claim.scope}</p>
          </div>
          <div className="compact-detail">
            <span>Decision impact</span>
            <p>{claim.decision_impact}</p>
          </div>
          {claim.provenance_note ? (
            <div className="compact-detail">
              <span>Provenance note</span>
              <p>{claim.provenance_note}</p>
            </div>
          ) : null}
        </div>
      </details>

      <section className="detail-section">
        <div className="section-heading-row">
          <h3>Relationships</h3>
          <span className="count-badge">{relationships.length}</span>
        </div>

        {relationships.length > 0 ? (
          <div className="source-list">
            {relationships.map((edge) => {
              const counterpart =
                edge.from === claim.id ? edge.to : edge.from;
              const direction =
                edge.from === claim.id ? "points to" : "receives from";

              return (
                <button
                  className="relationship-card relationship-button"
                  key={`${edge.from}->${edge.to}`}
                  onClick={() => onNavigateClaim(counterpart)}
                  aria-label={`Open related claim ${counterpart}`}
                >
                  <div className="relationship-line">
                    <span>{direction}</span>
                    <code>{counterpart}</code>
                    <span className="relationship-arrow">→</span>
                  </div>
                  <p>{edge.rationale}</p>
                </button>
              );
            })}
          </div>
        ) : (
          <EmptyMini>No declared graph edges for this claim.</EmptyMini>
        )}
      </section>

      <section className="detail-section">
        <div className="section-heading-row">
          <h3>Source files</h3>
          <span className="count-badge">{claim.source_files.length}</span>
        </div>

        {claim.source_files.length > 0 ? (
          <div className="source-list">
            {claim.source_files.map((source) => (
              <SourceFileCard key={source.ref} source={source} />
            ))}
          </div>
        ) : (
          <EmptyMini>No file provenance declared.</EmptyMini>
        )}
      </section>

      <section className="detail-section">
        <div className="section-heading-row">
          <h3>Database lineage</h3>
          <span className="count-badge">{claim.data_sources.length}</span>
        </div>

        {claim.data_sources.length > 0 ? (
          <div className="source-list">
            {claim.data_sources.map((source, index) => (
              <DataSourceCard
                key={`${source.system}-${source.table}-${index}`}
                source={source}
              />
            ))}
          </div>
        ) : (
          <EmptyMini>
            No database/table/query lineage declared for this claim.
          </EmptyMini>
        )}
      </section>

      <section className="detail-section provenance-footer">
        <div className="section-heading-row">
          <h3>Ledger record</h3>
          <CopyButton value={claim.record_ref} label="Copy record ref" compact />
        </div>
        <ReferenceValue value={claim.record_ref} />
        {claim.context_snapshot.repository_revision ? (
          <div className="revision-row">
            <span>snapshot</span>
            <code>
              {String(claim.context_snapshot.repository_revision).slice(0, 12)}
            </code>
            <CopyButton
              value={String(claim.context_snapshot.repository_revision)}
              label="Copy revision"
              compact
            />
          </div>
        ) : null}
      </section>
    </aside>
  );
}

function SourceFileCard({ source }: { source: SourceFile }) {
  return (
    <div className="source-card">
      <div className="source-card-topline">
        <ReferenceValue value={source.ref} />
        <CopyButton value={source.ref} label="Copy ref" compact />
      </div>
      <div className="role-row">
        {source.roles.map((role) => (
          <span className="role-pill" key={role}>
            {humanize(role)}
          </span>
        ))}
      </div>
      {source.note ? <p className="source-note">{source.note}</p> : null}
    </div>
  );
}

function DataSourceCard({ source }: { source: DataSource }) {
  const qualified = [
    source.catalog,
    source.database,
    source.schema,
    source.table,
  ]
    .filter(Boolean)
    .join(".");

  return (
    <div className="data-source-card">
      <div className="data-source-topline">
        <span className="system-pill">{source.system}</span>
        <div className="qualified-table">
          <code>{qualified || source.table}</code>
          <CopyButton
            value={qualified || source.table}
            label="Copy table"
            compact
          />
        </div>
      </div>

      {source.query.ref ? (
        <div className="query-meta-row">
          <span>query ref</span>
          <ReferenceValue value={source.query.ref} />
          <CopyButton value={source.query.ref} label="Copy query ref" compact />
        </div>
      ) : null}

      {source.query.sha256 ? (
        <div className="query-meta-row">
          <span>sha256</span>
          <code>{source.query.sha256.slice(0, 16)}…</code>
          <CopyButton value={source.query.sha256} label="Copy hash" compact />
        </div>
      ) : null}

      {source.query.text ? <QueryBlock text={source.query.text} /> : null}
      {source.note ? <p className="source-note">{source.note}</p> : null}
    </div>
  );
}

function QueryBlock({ text }: { text: string }) {
  return (
    <div className="query-block">
      <div className="query-block-head">
        <span>SQL / query text</span>
        <CopyButton value={text} label="Copy SQL" compact dark />
      </div>
      <pre>{text}</pre>
    </div>
  );
}

function ReferenceValue({ value }: { value: string }) {
  if (/^https?:\/\//i.test(value)) {
    return (
      <a className="reference-link" href={value} target="_blank" rel="noreferrer">
        {value}
      </a>
    );
  }
  return <code className="reference-code">{value}</code>;
}

function CopyButton({
  value,
  label,
  compact = false,
  dark = false,
}: {
  value: string;
  label: string;
  compact?: boolean;
  dark?: boolean;
}) {
  const [copied, setCopied] = useState(false);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1200);
    } catch {
      setCopied(false);
    }
  };

  return (
    <button
      className={[
        "copy-button",
        compact ? "compact" : "",
        dark ? "dark" : "",
      ]
        .filter(Boolean)
        .join(" ")}
      onClick={copy}
      title={label}
      aria-label={label}
    >
      {copied ? "Copied" : "Copy"}
    </button>
  );
}

function ProvenanceMetric({
  value,
  label,
  tone,
}: {
  value: number;
  label: string;
  tone: "present" | "missing" | "neutral";
}) {
  return (
    <div className={`provenance-metric ${tone}`}>
      <strong>{value}</strong>
      <span>{label}</span>
    </div>
  );
}

function FilterGroup({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  return (
    <div className="filter-group">
      <span className="filter-label">{label}</span>
      <div className="filter-buttons">{children}</div>
    </div>
  );
}

function FilterButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <button
      className={active ? "filter-button active" : "filter-button"}
      onClick={onClick}
      aria-pressed={active}
    >
      {children}
    </button>
  );
}

function DetailCell({ label, value }: { label: string; value: string }) {
  return (
    <div className="detail-cell">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function Metric({ value, label }: { value: number; label: string }) {
  return (
    <div className="metric">
      <strong>{value}</strong>
      <span>{label}</span>
    </div>
  );
}

function EmptyMini({ children }: { children: ReactNode }) {
  return <div className="empty-mini">{children}</div>;
}

function EmptyState({
  error,
  onRetry,
}: {
  error: string;
  onRetry: () => void;
}) {
  return (
    <main className="empty-state">
      <div className="empty-card">
        <div className="eyebrow">claim-contract / optional UI</div>
        <h1>Claim map data is missing.</h1>
        <p>{error}</p>
        <div className="recovery-actions">
          <button className="primary-button" onClick={onRetry}>
            Retry bundle load
          </button>
        </div>
        <div className="command-card">
          <code>claim-contract ui export</code>
          <code>cd ui &amp;&amp; npm install &amp;&amp; npm run dev</code>
        </div>
      </div>
    </main>
  );
}

function claimSearchText(claim: ClaimNode): string {
  const fileRefs = claim.source_files.map((source) => source.ref);
  const dataRefs = claim.data_sources.flatMap((source) => [
    source.system,
    source.catalog ?? "",
    source.database ?? "",
    source.schema ?? "",
    source.table,
    source.query.ref ?? "",
    source.query.text ?? "",
    source.note ?? "",
  ]);

  return [
    claim.id,
    claim.claim,
    claim.scope,
    claim.decision_impact,
    claim.record_ref,
    ...fileRefs,
    ...claim.source_files.map((source) => source.note ?? ""),
    ...dataRefs,
  ]
    .join(" ")
    .toLowerCase();
}

function humanize(value: string): string {
  return value
    .toLowerCase()
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function formatDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(date);
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

export default App;

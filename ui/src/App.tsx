import { useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { edgePath, layoutClaimGraph, nodeHeight, nodeWidth } from "./layout";
import type {
  ClaimGraphEdge,
  ClaimNode,
  ClaimUiBundle,
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

function App() {
  const [bundle, setBundle] = useState<ClaimUiBundle | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("ALL");

  useEffect(() => {
    let cancelled = false;
    fetch(bundleUrl)
      .then(async (response) => {
        if (!response.ok) {
          throw new Error(
            `Could not load ${bundleUrl} (HTTP ${response.status}). Run claim-contract ui export first.`,
          );
        }
        return (await response.json()) as ClaimUiBundle;
      })
      .then((payload) => {
        if (cancelled) return;
        if (payload.type !== "claim_contract.claim_ui_bundle") {
          throw new Error("The loaded JSON is not a claim-contract UI bundle.");
        }
        setBundle(payload);
        setSelectedId(payload.claims[0]?.id ?? null);
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        setLoadError(error instanceof Error ? error.message : String(error));
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const visibleClaims = useMemo(() => {
    if (!bundle) return [];
    const needle = query.trim().toLowerCase();
    return bundle.claims.filter((claim) => {
      const statusMatch = status === "ALL" || claim.status === status;
      const textMatch =
        !needle ||
        claim.id.toLowerCase().includes(needle) ||
        claim.claim.toLowerCase().includes(needle) ||
        claim.scope.toLowerCase().includes(needle);
      return statusMatch && textMatch;
    });
  }, [bundle, query, status]);

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
    bundle?.claims.find((claim) => claim.id === selectedId) ?? null;

  useEffect(() => {
    if (
      visibleClaims.length > 0 &&
      (!selectedId || !visibleIds.has(selectedId))
    ) {
      setSelectedId(visibleClaims[0].id);
    }
  }, [visibleClaims, visibleIds, selectedId]);

  if (loadError) {
    return <EmptyState error={loadError} />;
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
        <strong>Interpretation boundary.</strong> {bundle.scope_notice}
      </div>

      <section className="toolbar">
        <label className="search-field">
          <span>Search</span>
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Claim ID, wording, or scope…"
          />
        </label>
        <div className="status-filter" aria-label="Filter by claim status">
          <button
            className={status === "ALL" ? "filter-button active" : "filter-button"}
            onClick={() => setStatus("ALL")}
          >
            All
          </button>
          {statuses.map((candidate) => (
            <button
              key={candidate}
              className={
                status === candidate ? "filter-button active" : "filter-button"
              }
              onClick={() => setStatus(candidate)}
            >
              {humanize(candidate)}
            </button>
          ))}
        </div>
      </section>

      <section className="workspace">
        <ClaimGraph
          claims={visibleClaims}
          edges={visibleEdges}
          roots={bundle.graph.roots}
          selectedId={selectedId}
          onSelect={setSelectedId}
        />
        <ClaimInspector claim={selectedClaim} edges={bundle.graph.edges} />
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
}: {
  claims: ClaimNode[];
  edges: ClaimGraphEdge[];
  roots: string[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  const layout = useMemo(
    () => layoutClaimGraph(claims, edges, roots),
    [claims, edges, roots],
  );

  if (claims.length === 0) {
    return (
      <div className="graph-panel graph-empty">
        <p>No claims match the current filter.</p>
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
        <div className="graph-legend">
          <span><i className="legend-dot root" /> root</span>
          <span><i className="legend-dot open" /> open</span>
          <span><i className="legend-dot retired" /> retired</span>
        </div>
      </div>

      <div className="graph-scroll">
        <div
          className="graph-canvas"
          style={{ width: layout.width, height: layout.height }}
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
            </defs>
            {edges.map((edge) => {
              const source = layout.positions[edge.from];
              const target = layout.positions[edge.to];
              if (!source || !target) return null;
              return (
                <path
                  key={`${edge.from}->${edge.to}`}
                  d={edgePath(source, target)}
                  className="graph-edge"
                  markerEnd="url(#arrow)"
                >
                  <title>{edge.rationale}</title>
                </path>
              );
            })}
          </svg>

          {claims.map((claim) => {
            const position = layout.positions[claim.id];
            if (!position) return null;
            return (
              <button
                key={claim.id}
                className={[
                  "claim-node",
                  claim.is_root ? "root-node" : "",
                  claim.status === "RETIRED" ? "retired-node" : "",
                  selectedId === claim.id ? "selected" : "",
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
              >
                <div className="node-topline">
                  <span className="node-id">{claim.id}</span>
                  <span className={`status-dot status-${claim.status.toLowerCase()}`} />
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
  );
}

function ClaimInspector({
  claim,
  edges,
}: {
  claim: ClaimNode | null;
  edges: ClaimGraphEdge[];
}) {
  if (!claim) {
    return (
      <aside className="inspector empty-inspector">
        <p>Select a claim to inspect its provenance.</p>
      </aside>
    );
  }

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

      <section className="detail-section">
        <h3>Claim</h3>
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

      <section className="detail-section">
        <h3>Scope</h3>
        <p>{claim.scope}</p>
      </section>

      <section className="detail-section">
        <h3>Decision impact</h3>
        <p>{claim.decision_impact}</p>
      </section>

      <section className="detail-section">
        <div className="section-heading-row">
          <h3>Relationships</h3>
          <span className="count-badge">
            {edges.filter(
              (edge) => edge.from === claim.id || edge.to === claim.id,
            ).length}
          </span>
        </div>
        {edges.some(
          (edge) => edge.from === claim.id || edge.to === claim.id,
        ) ? (
          <div className="source-list">
            {edges
              .filter(
                (edge) => edge.from === claim.id || edge.to === claim.id,
              )
              .map((edge) => (
                <div
                  className="relationship-card"
                  key={`${edge.from}->${edge.to}`}
                >
                  <div className="relationship-line">
                    <code>{edge.from}</code>
                    <span>→</span>
                    <code>{edge.to}</code>
                  </div>
                  <p>{edge.rationale}</p>
                </div>
              ))}
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
        <h3>Ledger record</h3>
        <ReferenceLink value={claim.record_ref} />
        {claim.context_snapshot.repository_revision ? (
          <div className="revision-row">
            snapshot{" "}
            <code>
              {String(claim.context_snapshot.repository_revision).slice(0, 12)}
            </code>
          </div>
        ) : null}
      </section>
    </aside>
  );
}

function SourceFileCard({ source }: { source: SourceFile }) {
  return (
    <div className="source-card">
      <ReferenceLink value={source.ref} />
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
        <code>{qualified || source.table}</code>
      </div>
      {source.query.ref ? (
        <div className="query-ref">
          query ref · <ReferenceLink value={source.query.ref} />
        </div>
      ) : null}
      {source.query.sha256 ? (
        <div className="query-hash">
          sha256 · <code>{source.query.sha256.slice(0, 16)}…</code>
        </div>
      ) : null}
      {source.query.text ? <QueryBlock text={source.query.text} /> : null}
      {source.note ? <p className="source-note">{source.note}</p> : null}
    </div>
  );
}

function QueryBlock({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1200);
    } catch {
      setCopied(false);
    }
  };

  return (
    <div className="query-block">
      <div className="query-block-head">
        <span>SQL / query text</span>
        <button onClick={copy}>{copied ? "copied" : "copy"}</button>
      </div>
      <pre>{text}</pre>
    </div>
  );
}

function ReferenceLink({ value }: { value: string }) {
  if (/^https?:\/\//i.test(value)) {
    return (
      <a className="reference-link" href={value} target="_blank" rel="noreferrer">
        {value}
      </a>
    );
  }
  return <code className="reference-code">{value}</code>;
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

function EmptyState({ error }: { error: string }) {
  return (
    <main className="empty-state">
      <div className="empty-card">
        <div className="eyebrow">claim-contract / optional UI</div>
        <h1>Claim map data is missing.</h1>
        <p>{error}</p>
        <div className="command-card">
          <code>claim-contract ui export</code>
          <code>cd ui &amp;&amp; npm install &amp;&amp; npm run dev</code>
        </div>
      </div>
    </main>
  );
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

export default App;

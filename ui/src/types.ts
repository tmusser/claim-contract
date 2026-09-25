export type ClaimStatus =
  | "OPEN"
  | "SUPPORT_MET"
  | "REFUTE_MET"
  | "INCONCLUSIVE"
  | "RETIRED"
  | string;

export type ClaimClassification =
  | "ROOT"
  | "CONNECTED"
  | "PRUNE_CANDIDATE"
  | "RETIRED";

export interface ClaimGraphEdge {
  from: string;
  to: string;
  rationale: string;
}

export interface SourceFile {
  ref: string;
  roles: string[];
  note: string | null;
}

export interface QueryDescriptor {
  ref?: string;
  text?: string;
  sha256?: string;
}

export interface DataSource {
  system: string;
  catalog?: string;
  database?: string;
  schema?: string;
  table: string;
  query: QueryDescriptor;
  note?: string;
}

export interface ClaimNode {
  id: string;
  status: ClaimStatus;
  classification: ClaimClassification;
  is_root: boolean;
  claim: string;
  scope: string;
  decision_impact: string;
  logged_at: string;
  generated_at: string | null;
  record_ref: string;
  context_snapshot: {
    repository_revision?: string;
    refs?: string[];
    note?: string;
    [key: string]: unknown;
  };
  source_files: SourceFile[];
  data_sources: DataSource[];
  judgment: {
    last_evaluated?: string | null;
    judged_by?: string | null;
    evidence_refs?: string[];
    note?: string | null;
    [key: string]: unknown;
  };
}

export interface ClaimUiBundle {
  schema_version: "1.0";
  type: "claim_contract.claim_ui_bundle";
  scientific_validation: false;
  automatic_adjudication: false;
  read_only: true;
  scope_notice: string;
  generated_from: {
    ledger: string;
    graph: string;
    provenance: string | null;
  };
  graph: {
    scope_notice: string;
    roots: string[];
    edges: ClaimGraphEdge[];
  };
  claims: ClaimNode[];
}

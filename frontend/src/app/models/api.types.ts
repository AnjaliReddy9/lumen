export type ValidationSeverity = 'error' | 'warning';
export type ValidationCode =
  | 'syntax_error'
  | 'unknown_table'
  | 'unknown_column'
  | 'ambiguous_column'
  | 'unqualified_column';

export interface ValidationIssue {
  severity: ValidationSeverity;
  code: ValidationCode;
  message: string;
  table: string | null;
  column: string | null;
}

export interface ValidationResult {
  valid: boolean;
  issues: ValidationIssue[];
  parsed_sql: string | null;
}

export interface FilterClause {
  column_or_dimension: string;
  operator: string;
  value: string;
  confidence: 'high' | 'medium' | 'low';
}

export interface SortClause {
  column_or_dimension: string;
  direction: 'asc' | 'desc';
}

export interface QueryIntent {
  question: string;
  intent_summary: string;
  entities_referenced: string[];
  metrics_referenced: string[];
  dimensions_referenced: string[];
  time_grain: string | null;
  filters: FilterClause[];
  sort: SortClause | null;
  limit: number | null;
}

export type AmbiguityType =
  | 'dimension'
  | 'value'
  | 'metric'
  | 'time_range'
  | 'missing_filter'
  | 'join_path';

export interface AmbiguityIssue {
  type: AmbiguityType;
  description: string;
  options: string[];
  default: string | null;
}

export interface Interpretation {
  intent: QueryIntent;
  ambiguities: AmbiguityIssue[];
  confidence: 'high' | 'medium' | 'low';
}

export interface QueryRequest {
  question: string;
  resolutions?: Record<string, string> | null;
  skip_interpretation?: boolean;
  skip_validation?: boolean;
}

export interface QueryResponse {
  interpretation: Interpretation | null;
  generated_sql: string;
  validation: ValidationResult;
  rows: Record<string, unknown>[] | null;
  row_count: number;
  error: string | null;
  latency_ms: number;
  cost_usd: number;
}

export interface Column {
  name: string;
  data_type: string;
  nullable: boolean;
  is_primary_key: boolean;
}

export interface ForeignKey {
  from_column: string;
  to_table: string;
  to_column: string;
}

export interface Table {
  name: string;
  schema_name: string | null;
  columns: Column[];
  foreign_keys: ForeignKey[];
}

export interface Schema {
  tables: Table[];
}

export interface Dimension {
  name: string;
  column: string | null;
  expression: string | null;
  description: string | null;
}

export interface TimeDimension {
  name: string;
  column: string;
  granularity: string;
}

export interface Measure {
  expression: string;
  aggregation: string;
}

export interface Entity {
  name: string;
  description: string | null;
  table: string;
  primary_key: string;
  dimensions: Dimension[];
  time_dimensions: TimeDimension[];
}

export interface Metric {
  name: string;
  description: string | null;
  type: string;
  entity: string;
  measure: Measure;
  dimensions: string[];
  time_dimension: string | null;
}

export interface Relationship {
  from: string;
  from_key: string;
  to: string;
  to_key: string;
  type: string;
}

export interface SemanticModel {
  entities: Entity[];
  metrics: Metric[];
  relationships: Relationship[];
}

export interface EvalSummary {
  execution_accuracy: number;
  validation_pass_rate: number;
  generation_success_rate: number;
  avg_latency_ms: number;
  total_cost_usd: number;
  by_difficulty: Record<string, EvalSummary> | null;
}

export interface EvalResult {
  case_id: string;
  question: string;
  difficulty?: 'easy' | 'medium' | 'hard' | 'extra' | null;
  generated_sql: string | null;
  executed_rows: Record<string, unknown>[] | null;
  validation_valid: boolean;
  validation_issues: ValidationIssue[];
  interpretation_summary: string | null;
  attempts: number;
  latency_ms: number;
  cost_usd: number;
  execution_accuracy: boolean | null;
  error: string | null;
}

export interface EvalRun {
  run_id: string;
  benchmark: string;
  model: string;
  config: Record<string, unknown>;
  started_at: string;
  completed_at: string | null;
  cases_total: number;
  cases_completed: number;
  results: EvalResult[];
  summary: EvalSummary;
}

export interface EvalRunSummary {
  run_id: string;
  benchmark: string;
  model?: string;
  cases_completed: number;
  cases_total?: number;
  started_at?: string;
  execution_accuracy?: number;
  validation_pass_rate?: number;
  generation_success_rate?: number;
  total_cost_usd?: number;
  path: string;
}

export type StreamPhase =
  | 'interpreting'
  | 'generated_sql'
  | 'validating'
  | 'executing'
  | 'done'
  | 'error';

export interface StreamEvent {
  phase: StreamPhase;
  detail?: string;
  sql?: string;
  valid?: boolean;
  row_count?: number;
  payload?: QueryResponse;
}

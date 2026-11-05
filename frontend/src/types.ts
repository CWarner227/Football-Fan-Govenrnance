export type Config = Record<string, unknown>;
export interface Schema {
  type?: string;
  title?: string;
  description?: string;
  $ref?: string;
  $defs?: Record<string, Schema>;
  properties?: Record<string, Schema>;
  additionalProperties?: boolean | Schema;
  required?: string[];
  items?: Schema;
  prefixItems?: Schema[];
  anyOf?: Schema[];
  enum?: unknown[];
  default?: unknown;
  minimum?: number;
  maximum?: number;
  exclusiveMinimum?: number;
  minLength?: number;
  minItems?: number;
  maxItems?: number;
  format?: string;
  pattern?: string;
}
export interface Model {
  id: string;
  name: string;
  category: string;
  description?: string;
  schema: Schema;
  defaults: Config;
}
export interface Integration {
  id: string;
  name: string;
  enabled: boolean;
  capabilities: string[];
  status?: string;
}
export interface Capabilities {
  version: string;
  schema: Schema;
  defaults: Config;
  limits: Config;
  integrations: Integration[];
}
export interface Run {
  id: string;
  name: string;
  description: string;
  kind: "simulation" | "experiment";
  status: "queued" | "running" | "completed" | "failed" | "cancelled";
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  elapsed_seconds: number;
  configuration: Config;
  seed: number;
  engine_version: string;
  error: string | null;
  progress: {
    completed_trials: number | null;
    total_trials: number;
    percentage: number | null;
  };
}
export interface Scenario {
  id: string;
  name: string;
  description: string;
  category: string;
  configuration: Config;
  population_size: number;
  voting_models: string[];
  attacks: string[];
  defenses: string[];
  duration_months: number;
}
export interface SavedConfig {
  id: string;
  name: string;
  description: string;
  configuration: Config;
  created_at: string;
}
export interface Page<T> {
  items: T[];
  total: number;
  offset?: number;
  limit?: number;
  columns?: string[];
}
export type Row = Record<string, unknown>;
export interface Comparison {
  runs: { run: Run; summary: Page<Row> }[];
  warnings: string[];
  differences: { path: string; values: Record<string, unknown> }[];
  paired_differences: Row[];
}

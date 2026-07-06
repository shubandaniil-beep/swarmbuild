export interface Project {
  project_id: string;
  title: string;
  brief: string;
  budget_usd: number;
  requested_outputs: string[];
  project_type: string;
  project_mode: string;
  requires_codebase: boolean;
  technical_level: string;
  user_goal: string;
  parent_project_id: string | null;
  status: string;
  estimated_complexity: string;
  estimated_workflow_size?: string;
  estimated_swarm_size?: number;
  current_phase: string | null;
  personality_mode?: string;
  credits_estimate?: number;
  credits_spent?: number;
  credits_remaining?: number | null;
  credits_per_usd?: number;
  demo_run?: boolean;
  billing_mode?: "client" | "admin_bypass" | "client_simulation" | "missing_owner" | string;
  client_billing_enabled?: boolean;
  zero_credit_reason?: string;
  billing_note?: string;
  // release gate: only a released, ready project may be downloaded by a client.
  downloadable?: boolean;
  release_decision?: string | null;
  budget: BudgetState | null;
  created_at: string | null;
}

export interface BudgetState {
  user_budget_usd: number;
  platform_fee_usd?: number;
  model_budget_usd?: number;
  compute_budget_usd?: number;
  reserve_budget_usd?: number;
  spent_usd: number;
  remaining_usd: number;
  saving_mode?: boolean;
  status: string;
}

export interface Phase {
  phase_key: string;
  label?: string;
  status: string;
  budget_limit_usd: number;
  spent_estimated_usd: number;
  decision: string | null;
  started_at: string | null;
  finished_at: string | null;
}

export interface ProjectEvent {
  type: string;
  message: string;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface ArtifactInfo {
  id: string;
  artifact_type: string;
  path: string;
  display_name: string;
  safety_status?: "quarantine" | "safe_to_download" | "blocked";
}

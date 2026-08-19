export type ExperimentDelta = {
  fixed: number;
  adaptive: number;
  difference: number;
  percent_change: number | null;
  adaptive_direction: "better" | "worse" | "same" | string;
  lower_is_better: boolean;
};

export type ExperimentWaitDistribution = {
  count: number;
  average_seconds: number;
  median_seconds: number;
  p95_seconds: number;
  max_seconds: number;
  total_seconds: number;
};

export type ExperimentQueueDistribution = {
  sample_count: number;
  average: number;
  p95: number;
  max: number;
  queue_seconds: number;
  occupied_seconds: number;
  occupied_share_percent: number;
};

export type ExperimentTimelinePoint = {
  t: number;
  phase: string;
  phase_key: string;
  vehicle_queue: number;
  pedestrian_queue: number;
  vehicle_passages: number;
  pedestrian_crossings: number;
  active_rules: string[];
};

export type ExperimentModeResult = {
  mode: "fixed" | "adaptive";
  metrics: {
    waiting: {
      vehicle: ExperimentWaitDistribution;
      pedestrian: ExperimentWaitDistribution;
    };
    queues: {
      vehicle: ExperimentQueueDistribution;
      pedestrian: ExperimentQueueDistribution;
      simultaneous_queue_seconds: number;
      simultaneous_queue_share_percent: number;
    };
    throughput: {
      vehicle_passages: number;
      pedestrian_crossings: number;
      vehicle_per_minute: number;
      pedestrian_per_minute: number;
      combined_services: number;
      combined_services_per_minute: number;
      vehicle_passages_per_green_minute: number;
    };
    signal: {
      phase_time_seconds: Record<string, number>;
      phase_share_percent: Record<string, number>;
      phase_transitions: number;
      cycles_completed: number;
      clearance_time_seconds: number;
      clearance_share_percent: number;
      rule_application_count: number;
      rule_applications: Record<string, number>;
      extension_seconds: number;
      reduction_seconds: number;
    };
    diagnostics: {
      protected_overlap_seconds: number;
      protected_overlap_detected: boolean;
      note: string;
    };
  };
  final_signal: Record<string, unknown> | null;
  timeline: ExperimentTimelinePoint[];
};

export type SimulationExperiment = {
  run_id: string;
  created_at_ms: number;
  label: string;
  scenario: {
    duration_seconds: number;
    density: "light" | "normal" | "busy";
    seed: number;
    sample_interval_seconds: number;
    profile: string;
    comparison: ["fixed", "adaptive"];
  };
  fixed: ExperimentModeResult;
  adaptive: ExperimentModeResult;
  comparison: Record<string, ExperimentDelta>;
  prototype_only: boolean;
  scope_note: string;
};

export type SimulationExperimentSummary = {
  run_id: string;
  created_at_ms: number;
  label: string;
  scenario: SimulationExperiment["scenario"];
  headline: Record<string, ExperimentDelta | undefined>;
};

export type SimulationExperimentList = {
  experiments: SimulationExperimentSummary[];
  total: number;
  storage_path: string;
  prototype_only: boolean;
};

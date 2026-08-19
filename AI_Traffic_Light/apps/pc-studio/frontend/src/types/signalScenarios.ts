import type {
  SignalRulesConfig as BaseSignalRulesConfig,
  SignalStatus as BaseSignalStatus,
  TrafficState,
} from "../types";

export type ScenarioConditionSource = "metric" | "zone_class_count";
export type ScenarioOperator = "gt" | "gte" | "lt" | "lte" | "eq";
export type ScenarioMatch = "all" | "any";
export type ScenarioActionType =
  | "extend_current_phase"
  | "reduce_current_phase"
  | "hold_current_phase"
  | "request_next_phase"
  | "incident_hold";
export type ScenarioRequestService = "pedestrian" | "vehicle" | null;

export type SignalMetric =
  | "pedestrians_crossing"
  | "crossing_dwell_seconds"
  | "pedestrians_waiting"
  | "pedestrian_wait_seconds"
  | "vehicles_waiting"
  | "vehicle_wait_seconds"
  | "mobility_assistance"
  | "incident_person_fallen";

export type MetricScenarioCondition = {
  source: "metric";
  metric: SignalMetric;
  operator: ScenarioOperator;
  threshold: number;
};

export type ZoneClassScenarioCondition = {
  source: "zone_class_count";
  zone_id: string;
  class_name: string;
  operator: ScenarioOperator;
  threshold: number;
};

export type ScenarioCondition = MetricScenarioCondition | ZoneClassScenarioCondition;

export type SignalScenarioAction = {
  type: ScenarioActionType;
  adjustment_seconds: number;
  target_phases: string[];
  request_service: ScenarioRequestService;
};

export type SignalScenario = {
  id: string;
  label: string;
  enabled: boolean;
  rank: number;
  match: ScenarioMatch;
  conditions: ScenarioCondition[];
  persistence_seconds: number;
  cooldown_seconds: number;
  action: SignalScenarioAction;
};

export type ScenarioProfile = BaseSignalRulesConfig["profiles"][string] & {
  scenarios: SignalScenario[];
};

export type ScenarioSignalRulesConfig = Omit<BaseSignalRulesConfig, "profiles"> & {
  profiles: Record<string, ScenarioProfile>;
};

export type ScenarioConditionStatus = {
  source: ScenarioConditionSource;
  label: string;
  operator: ScenarioOperator;
  threshold: number;
  observed: number;
  matched: boolean;
  available: boolean;
};

export type SignalScenarioStatus = {
  scenario_id: string;
  rule_id: string;
  label: string;
  rank: number;
  priority: number;
  state: "winner" | "triggered" | "suppressed" | "inactive" | "unavailable" | string;
  reason: string;
  stable_for_seconds: number;
  condition_match: ScenarioMatch;
  conditions: ScenarioConditionStatus[];
  action: SignalScenarioAction;
  eligible: boolean;
  matched: boolean;
};

export type ScenarioSignalStatus = BaseSignalStatus & {
  winning_scenario_id: string | null;
  winning_scenario_label: string | null;
  active_scenarios: string[];
  scenario_status: SignalScenarioStatus[];
  observations: BaseSignalStatus["observations"] & {
    zone_class_counts?: Record<string, Record<string, number>>;
  };
};

export type ScenarioTrafficState = TrafficState & {
  zone_class_counts?: Record<string, Record<string, number>>;
};

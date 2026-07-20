export const APP_VERSION = '0.1.0';

export type AgentState = 'idle' | 'thinking' | 'planning' | 'executing' | 'learning' | 'self_modifying' | 'waiting' | 'running' | 'training' | 'error' | 'paused' | 'demo';

export interface AgentStatus {
  state: AgentState;
  iteration: number;
  uptime: number;
  mood: string;
  activeGoal: string | null;
  drives: IntrinsicDrives;
  memory: MemoryStats;
  crawlers: CrawlerStats;
  maldoror: MaldororStats;
  production: ProductionStats;
  knowledge?: KnowledgeStats;
  selfReflection?: Record<string, unknown>;
  rlAgent?: Record<string, unknown>;
  curiosity?: Record<string, unknown>;
  metacognition?: Record<string, unknown>;
  demo?: DemoStats;
}

export interface IntrinsicDrives {
  curiosity: number;
  mastery: number;
  competence: number;
  autonomy: number;
  novelty: number;
}

export interface MemoryStats {
  working: number;
  episodic: number;
  semantic: number;
  procedural: number;
}

export interface CrawlerStats {
  active: number;
  total: number;
  requestsToday: number;
  bandwidthUsed: number;
}

export interface MaldororStats {
  version: string;
  qualityGate: 'pass' | 'fail' | 'pending';
  improvementPct: number;
  lastTrainingLoss: number;
}

export interface ProductionStats {
  latency: number;
  qualityScore: number;
  errorRate: number;
  circuitBreaker: 'closed' | 'open' | 'half-open';
}

export interface KnowledgeStats {
  nodes: number;
  edges: number;
}

export interface ActivityEvent {
  id: string;
  timestamp: number;
  type: 'action' | 'learning' | 'modification' | 'error' | 'training' | 'acquisition' | 'demo';
  message: string;
  metadata?: Record<string, unknown>;
}

export interface Goal {
  id: string;
  description: string;
  status: 'pending' | 'active' | 'completed' | 'failed';
  progress: number;
  priority: 'low' | 'medium' | 'high' | 'critical';
  subgoals?: Goal[];
}

export interface MemoryRecord {
  id: string;
  type: 'episodic' | 'semantic' | 'procedural' | 'working';
  content: string;
  strength: number;
  accessCount: number;
  createdAt: number;
}

export interface KnowledgeNode {
  id: string;
  name: string;
  type: string;
  connections: number;
  strength: number;
}

export interface KnowledgeEdge {
  source: string;
  target: string;
  type: string;
  weight: number;
}

export interface MuJoCoStats {
  connected: boolean;
  bodies: number;
  joints: number;
  fps: number;
  robotModel: string;
}

export interface DemoSubsystem {
  name: string;
  [key: string]: unknown;
}

export interface DemoStats {
  active: boolean;
  step: number;
  totalSteps: number;
  stepName: string;
  goal: string;
  evidenceCount: number;
  memoryWrites: number;
  reflectionSummary: string | null;
  maldororProposal: string | null;
  startedAt: number | null;
  subsystems?: Record<string, DemoSubsystem>;
  maldororPipeline?: {
    stages: { name: string; status: string; description: string; input_sources: string[]; metrics: Record<string, unknown> }[];
    version: string;
    quality_gate: string;
    improvement_pct: number;
    last_training_loss: number;
    total_improvements: number;
    rollback_count: number;
  };
  runtimeMetrics?: {
    latency_ms: number;
    error_rate: number;
    uptime_sec: number;
    requests_per_sec: number;
    active_connections: number;
    cpu_usage_pct: number;
    memory_usage_mb: number;
    gc_collections: number;
    event_loop_utilization: number;
  };
  behaviorStats?: {
    queries_total: number;
    discoveries_total: number;
    modifications_total: number;
    reflections_total: number;
    improvements_total: number;
    curiosity_score: number;
    mastery_score: number;
    competence_score: number;
    autonomy_score: number;
    session_duration_sec: number;
    avg_response_time_ms: number;
  };
  modelRouting?: {
    current_model: string;
    available_models: string[];
    routing_table: { task_type: string; model: string; reason: string }[];
    decisions_this_session: number;
    avg_latency_ms: number;
    fallback_count: number;
  };
  loadingStages?: { stage: number; name: string; description: string; duration_ms: number }[];
}

export interface DemoReflection {
  what_worked: string;
  what_failed: string;
  lesson: string;
  root_cause: string;
}

export interface DemoMaldororProposal {
  description: string;
  reasoning: string;
  dry_run_diff: string;
  validation: {
    syntax_valid: boolean;
    import_safe: boolean;
    sandbox_passed: boolean;
    applied: boolean;
  };
}

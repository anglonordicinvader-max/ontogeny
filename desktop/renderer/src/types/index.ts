export type AgentState = 'idle' | 'thinking' | 'planning' | 'executing' | 'learning' | 'self_modifying' | 'waiting' | 'running' | 'training' | 'error' | 'paused';

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
  type: 'action' | 'learning' | 'modification' | 'error' | 'training' | 'crawl';
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

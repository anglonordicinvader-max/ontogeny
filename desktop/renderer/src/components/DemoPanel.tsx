import { useState, useEffect, useCallback } from 'react';
import { Panel, MetricCard } from './Panel';
import { cn } from '@/lib/utils';
import type { AgentStatus, DemoReflection, DemoMaldororProposal } from '@/types';
import {
  Play,
  Pause,
  RotateCcw,
  ChevronRight,
  CheckCircle2,
  Circle,
  Target,
  Database,
  Zap,
  FileText,
  ArrowRight,
  Activity,
  Cpu,
  GitBranch,
  Layers,
  Eye,
  BarChart3,
  Workflow,
  Box,
} from 'lucide-react';

interface DemoPanelProps {
  status: AgentStatus | null;
  send: (type: string, payload?: unknown) => void;
  backendPort: number;
}

// ─── Subsystem chip icons ─────────────────────────────────────────────

const SUBSYSTEM_ICONS: Record<string, React.FC<{ className?: string }>> = {
  knowledge_acquisition: Workflow,
  persistent_memory: Database,
  knowledge_graph: GitBranch,
  goal_management: Target,
  planning: Layers,
  reflection: Eye,
  neocorpus: Box,
  runtime_diagnostics: Activity,
  behavior_stats: BarChart3,
  model_routing: Zap,
};

const SUBSYSTEM_ORDER = [
  'knowledge_acquisition',
  'persistent_memory',
  'knowledge_graph',
  'goal_management',
  'planning',
  'reflection',
  'neocorpus',
  'runtime_diagnostics',
  'behavior_stats',
  'model_routing',
] as const;

// ─── Subsystem chip ───────────────────────────────────────────────────

function SubsystemChip({ subsystemKey, data, active }: { subsystemKey: string; data: Record<string, unknown>; active: boolean }) {
  const Icon = SUBSYSTEM_ICONS[subsystemKey] || Circle;
  const name = String(data.name || subsystemKey);
  const isActive = active;
  const metric = getSubsystemMetric(subsystemKey, data);

  return (
    <div className={cn(
      'flex items-center gap-2 px-2.5 py-1.5 rounded-md border transition-all text-xs',
      isActive
        ? 'bg-surface-4 border-accent/20 text-text-primary'
        : 'bg-surface-2 border-border-subtle text-text-tertiary opacity-60'
    )}>
      <div className={cn(
        'w-1.5 h-1.5 rounded-full shrink-0',
        isActive ? 'bg-status-success animate-pulse' : 'bg-text-tertiary'
      )} />
      <Icon className={cn('w-3.5 h-3.5 shrink-0', isActive ? 'text-accent' : 'text-text-tertiary')} />
      <div className="flex-1 min-w-0">
        <div className="text-[11px] font-medium truncate">{name}</div>
        {metric && <div className="text-[10px] text-text-tertiary truncate">{metric}</div>}
      </div>
    </div>
  );
}

function getSubsystemMetric(key: string, data: Record<string, unknown>): string {
  if (key === 'knowledge_acquisition') return `${data.engines_active || 0}/${data.engines_total || 30} engines`;
  if (key === 'persistent_memory') return `${data.total_records || 0} records`;
  if (key === 'knowledge_graph') return `${data.nodes || 0} nodes, ${data.edges || 0} edges`;
  if (key === 'goal_management') return `${data.active_goals || 0} active, ${data.completed_goals || 0} done`;
  if (key === 'planning') return `${data.steps_completed || 0}/${data.steps_total || 0} steps`;
  if (key === 'reflection') return `${data.insights_generated || 0} insights`;
  if (key === 'neocorpus') {
    const sims = data.connected_simulators as string[] | undefined;
    return sims ? sims.join(', ') : 'Offline';
  }
  if (key === 'runtime_diagnostics') return `${data.latency_ms || 0}ms latency`;
  if (key === 'behavior_stats') return `${data.total_queries || 0} queries`;
  if (key === 'model_routing') return String(data.current_model || '—');
  return '';
}

// ─── Maldoror pipeline stage ──────────────────────────────────────────

function MaldororStage({ stage, index, isActive, isCompleted }: {
  stage: { name: string; status: string; description: string; metrics: Record<string, unknown> };
  index: number;
  isActive: boolean;
  isCompleted: boolean;
}) {
  return (
    <div className="flex gap-3">
      <div className="flex flex-col items-center">
        <div className={cn(
          'w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold border-2 transition-all',
          isCompleted && 'bg-status-success/20 border-status-success text-status-success',
          isActive && 'bg-accent/20 border-accent text-accent animate-pulse',
          !isCompleted && !isActive && 'bg-surface-2 border-border-subtle text-text-tertiary'
        )}>
          {isCompleted ? <CheckCircle2 className="w-3.5 h-3.5" /> : index + 1}
        </div>
        {index < 5 && <div className={cn('w-px flex-1 min-h-[20px] my-1', isCompleted ? 'bg-status-success/30' : 'bg-border-subtle')} />}
      </div>
      <div className="flex-1 pb-2">
        <div className="flex items-center gap-2">
          <span className={cn('text-xs font-medium', isActive ? 'text-text-primary' : isCompleted ? 'text-text-secondary' : 'text-text-tertiary')}>
            {stage.name}
          </span>
          {isActive && <span className="text-[9px] px-1.5 py-0.5 rounded bg-accent/15 text-accent font-medium">ACTIVE</span>}
        </div>
        <div className="text-[11px] text-text-tertiary mt-0.5 leading-relaxed">{stage.description}</div>
        {isCompleted && stage.metrics && (
          <div className="flex flex-wrap gap-1 mt-1">
            {Object.entries(stage.metrics).slice(0, 3).map(([k, v]) => (
              <span key={k} className="text-[9px] px-1.5 py-0.5 rounded bg-surface-3 text-text-tertiary">
                {k.replace(/_/g, ' ')}: {String(v)}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Loading stage bar ────────────────────────────────────────────────

function LoadingStageBar({ stage, completed, active, index }: {
  stage: { name: string; description: string; duration_ms: number };
  completed: boolean;
  active: boolean;
  index: number;
}) {
  return (
    <div className={cn(
      'flex items-center gap-2.5 px-3 py-2 rounded-md transition-all text-xs',
      completed && 'bg-status-success/5',
      active && 'bg-accent/10',
      !completed && !active && 'bg-surface-2 opacity-40'
    )}>
      <div className={cn(
        'w-5 h-5 rounded flex items-center justify-center text-[10px] font-bold shrink-0',
        completed && 'bg-status-success/20 text-status-success',
        active && 'bg-accent/20 text-accent animate-pulse',
        !completed && !active && 'bg-surface-3 text-text-tertiary'
      )}>
        {completed ? <CheckCircle2 className="w-3 h-3" /> : index + 1}
      </div>
      <div className="flex-1 min-w-0">
        <div className={cn('text-[11px] font-medium', completed || active ? 'text-text-secondary' : 'text-text-tertiary')}>
          {stage.name}
        </div>
        <div className="text-[10px] text-text-tertiary truncate">{stage.description}</div>
      </div>
      <div className="text-[10px] text-text-tertiary tabular-nums shrink-0">{stage.duration_ms}ms</div>
    </div>
  );
}

// ─── Model routing row ────────────────────────────────────────────────

function ModelRoutingRow({ decision }: { decision: { task_type: string; model: string; reason: string } }) {
  return (
    <div className="flex items-center gap-2 text-[11px] py-1 border-b border-border-subtle last:border-0">
      <span className="text-text-secondary font-mono truncate w-28">{decision.task_type.replace(/_/g, ' ')}</span>
      <ArrowRight className="w-3 h-3 text-text-tertiary shrink-0" />
      <span className="text-accent font-medium truncate">{decision.model}</span>
      <span className="text-text-tertiary text-[10px] ml-auto truncate">{decision.reason}</span>
    </div>
  );
}

// ─── Main DemoPanel ───────────────────────────────────────────────────

export function DemoPanel({ status, send, backendPort }: DemoPanelProps) {
  const demo = status?.demo;
  const [autoPlay, setAutoPlay] = useState(false);
  const [evidence, setEvidence] = useState<Record<string, unknown>[]>([]);
  const [reflection, setReflection] = useState<DemoReflection | null>(null);
  const [maldoror, setMaldoror] = useState<DemoMaldororProposal | null>(null);
  const [knowledgeGraph, setKnowledgeGraph] = useState<{ nodes: Record<string, unknown>[]; edges: Record<string, unknown>[] }>({ nodes: [], edges: [] });

  const advance = useCallback(() => {
    send('command', { command: 'demo_advance' });
  }, [send]);

  const reset = useCallback(() => {
    send('command', { command: 'demo_reset' });
    setEvidence([]);
    setReflection(null);
    setMaldoror(null);
    setKnowledgeGraph({ nodes: [], edges: [] });
  }, [send]);

  const start = useCallback(() => {
    send('command', { command: 'demo_start' });
  }, [send]);

  useEffect(() => {
    if (!autoPlay || !demo?.active) return;
    if (demo.step >= demo.totalSteps) {
      setAutoPlay(false);
      return;
    }
    const timer = setTimeout(advance, 1800);
    return () => clearTimeout(timer);
  }, [autoPlay, demo?.active, demo?.step, demo?.totalSteps, advance]);

  useEffect(() => {
    if (!demo?.active) return;
    const base = `http://127.0.0.1:${backendPort}`;
    fetch(`${base}/api/demo/evidence`).then(r => r.json()).then((d: Record<string, unknown>[]) => setEvidence(d)).catch(() => {});
    fetch(`${base}/api/demo/reflection`).then(r => r.json()).then((d: DemoReflection | null) => setReflection(d)).catch(() => {});
    fetch(`${base}/api/demo/maldoror`).then(r => r.json()).then((d: DemoMaldororProposal | null) => setMaldoror(d)).catch(() => {});
    fetch(`${base}/api/demo/knowledge-graph`).then(r => r.json()).then((d: { nodes: Record<string, unknown>[]; edges: Record<string, unknown>[] }) => setKnowledgeGraph(d)).catch(() => {});
  }, [demo?.active, demo?.step, backendPort]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;
      if (e.code === 'Space' && demo?.active && demo.step < demo.totalSteps) {
        e.preventDefault();
        advance();
      }
      if (e.code === 'KeyR' && e.ctrlKey) {
        e.preventDefault();
        reset();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [demo?.active, demo?.step, demo?.totalSteps, advance, reset]);

  const subsystems = demo?.subsystems as Record<string, Record<string, unknown>> | undefined;
  const pipeline = demo?.maldororPipeline as { stages: { name: string; status: string; description: string; input_sources: string[]; metrics: Record<string, unknown> }[]; version: string; total_improvements: number } | undefined;
  const runtime = demo?.runtimeMetrics as { latency_ms: number; error_rate: number; uptime_sec: number; gpu_usage_pct: number; memory_usage_mb: number } | undefined;
  const behavior = demo?.behaviorStats as { curiosity_score: number; mastery_score: number; competence_score: number; autonomy_score: number; queries_total: number; discoveries_total: number; reflections_total: number; improvements_total: number } | undefined;
  const routing = demo?.modelRouting as { current_model: string; routing_table: { task_type: string; model: string; reason: string }[]; avg_latency_ms: number; fallback_count: number } | undefined;
  const loadingStages = demo?.loadingStages as { stage: number; name: string; description: string; duration_ms: number }[] | undefined;

  // ── Pre-start screen ──────────────────────────────────────────────

  if (!demo?.active) {
    return (
      <div className="h-full overflow-y-auto p-4 space-y-4 animate-panel-in">
        <Panel title="Cognitive Architecture" accentGlow>
          <div className="space-y-4">
            <div className="text-sm text-text-secondary leading-relaxed">
              Run a guided demonstration of Ontogeny's integrated cognitive workflow.
              This walkthrough uses controlled demonstration fixtures based on real system outputs.
            </div>
            <div className="text-xs text-text-tertiary space-y-1">
              <div className="font-medium text-text-secondary mb-2">Architecture overview:</div>
              <div className="flex items-center gap-2"><ArrowRight className="w-3 h-3 text-accent" /> 30 knowledge acquisition engines</div>
              <div className="flex items-center gap-2"><ArrowRight className="w-3 h-3 text-accent" /> 4-layer persistent memory</div>
              <div className="flex items-center gap-2"><ArrowRight className="w-3 h-3 text-accent" /> Maldoror recursive self-improvement</div>
              <div className="flex items-center gap-2"><ArrowRight className="w-3 h-3 text-accent" /> NeoCorpus embodiment abstraction</div>
              <div className="flex items-center gap-2"><ArrowRight className="w-3 h-3 text-accent" /> Hybrid model routing (Qwen2.5:72B, DeepSeek-Coder-V2:16B, Llama3.2, Maldoror)</div>
            </div>
            <div className="flex gap-2">
              <button onClick={start} className="btn-primary-glass flex items-center gap-2">
                <Play className="w-4 h-4" /> Start Demo
              </button>
            </div>
            <div className="text-2xs text-text-tertiary mt-2">
              Controlled demonstration — no live LLM calls, no network requests, no source code modification.
            </div>
            <div className="text-2xs text-text-tertiary mt-1">
              Keyboard: Space = next step, Ctrl+R = reset
            </div>
          </div>
        </Panel>
      </div>
    );
  }

  const currentStep = demo.step;
  const totalSteps = demo.totalSteps;
  const isStep1 = currentStep === 1;
  const isFinal = currentStep >= totalSteps;

  return (
    <div className="h-full overflow-y-auto p-4 space-y-4 animate-panel-in">
      {/* ── Demo banner ──────────────────────────────────────────── */}
      <div className="flex items-center gap-2 px-3 py-1.5 rounded bg-status-success/10 border border-status-success/20 text-2xs text-status-success">
        <Play className="w-3 h-3" />
        <span className="font-medium">Deterministic Demo Mode</span>
        <span className="text-status-success/60">— cognitive architecture walkthrough</span>
      </div>

      {/* ── Controls ─────────────────────────────────────────────── */}
      <Panel title={isStep1 ? 'System Initialization' : `Step ${currentStep} / ${totalSteps}`} accentGlow>
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-status-success animate-pulse" />
            <span className="text-xs text-text-secondary font-medium">
              {isStep1 ? 'Initializing subsystems...' : demo.stepName}
            </span>
          </div>
          <div className="flex gap-1">
            <button
              onClick={() => setAutoPlay(!autoPlay)}
              className="btn-ghost p-1.5"
              title={autoPlay ? 'Pause' : 'Auto-play'}
            >
              {autoPlay ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
            </button>
            <button onClick={advance} className="btn-ghost p-1.5" title="Next step (Space)" disabled={currentStep >= totalSteps}>
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
            <button onClick={reset} className="btn-ghost p-1.5" title="Reset (Ctrl+R)">
              <RotateCcw className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
        <div className="w-full bg-surface-2 rounded-full h-1.5 mb-2">
          <div
            className="bg-accent h-1.5 rounded-full transition-all duration-500"
            style={{ width: `${(currentStep / totalSteps) * 100}%` }}
          />
        </div>
        <div className="flex justify-between text-2xs text-text-tertiary">
          <span>{currentStep} of {totalSteps} stages</span>
          <span>{Math.round((currentStep / totalSteps) * 100)}%</span>
        </div>
      </Panel>

      {/* ── Loading sequence (step 1) ────────────────────────────── */}
      {isStep1 && loadingStages && (
        <Panel title="Initialization Sequence">
          <div className="space-y-1">
            {loadingStages.map((stage, i) => {
              const isCompleted = i < 0;
              const isActive = i === 0;
              return (
                <LoadingStageBar key={i} stage={stage} completed={isCompleted} active={isActive} index={i} />
              );
            })}
          </div>
        </Panel>
      )}

      {/* ── Step list ────────────────────────────────────────────── */}
      {!isStep1 && (
        <Panel title="Cognitive Pipeline">
          <div className="space-y-1">
            {DEMO_STEP_NAMES.map((name, i) => {
              const stepNum = i + 1;
              const isCompleted = stepNum < currentStep;
              const isCurrent = stepNum === currentStep;
              const Icon = STEP_ICONS[i] || Circle;
              return (
                <div
                  key={i}
                  className={cn(
                    'flex items-center gap-2 py-1.5 px-2 rounded text-xs transition-all',
                    isCompleted && 'text-text-secondary',
                    isCurrent && 'text-text-primary bg-surface-2',
                    !isCompleted && !isCurrent && 'text-text-tertiary opacity-40'
                  )}
                >
                  {isCompleted ? (
                    <CheckCircle2 className="w-3.5 h-3.5 text-status-success shrink-0" />
                  ) : (
                    <Icon className={cn('w-3.5 h-3.5 shrink-0', isCurrent ? 'text-accent' : 'text-text-tertiary')} />
                  )}
                  <span className="truncate">{name}</span>
                </div>
              );
            })}
          </div>
        </Panel>
      )}

      {/* ── Subsystem status chips ───────────────────────────────── */}
      {subsystems && Object.keys(subsystems).length > 0 && (
        <Panel title="Cognitive Architecture">
          <div className="grid grid-cols-2 gap-1.5">
            {SUBSYSTEM_ORDER.map((key) => {
              const data = subsystems[key];
              if (!data) return null;
              return <SubsystemChip key={key} subsystemKey={key} data={data} active={true} />;
            })}
          </div>
        </Panel>
      )}

      {/* ── Maldoror pipeline ────────────────────────────────────── */}
      {pipeline && pipeline.stages && (
        <Panel title="Maldoror Recursive Engine" accentGlow>
          <div className="mb-2 flex items-center gap-2">
            <Zap className="w-3.5 h-3.5 text-accent" />
            <span className="text-[11px] text-text-secondary">
              Pipeline v{pipeline.version} — {pipeline.total_improvements} improvements applied
            </span>
          </div>
          <div className="space-y-0">
            {pipeline.stages.map((stage, i) => {
              const isCompleted = stage.status === 'completed';
              const isActive = stage.status === 'active';
              return (
                <MaldororStage
                  key={i}
                  stage={stage}
                  index={i}
                  isActive={isActive}
                  isCompleted={isCompleted}
                />
              );
            })}
          </div>
        </Panel>
      )}

      {/* ── Live cognitive status ────────────────────────────────── */}
      {(runtime || behavior || routing) && (
        <Panel title="Live Cognitive Status">
          <div className="space-y-3">
            {/* Runtime metrics */}
            {runtime && (
              <div className="grid grid-cols-3 gap-2">
                <MetricCard label="Latency" value={`${runtime.latency_ms}ms`} />
                <MetricCard label="Uptime" value={`${Math.round(runtime.uptime_sec / 60)}m`} />
                <MetricCard label="Errors" value={`${(runtime.error_rate * 100).toFixed(1)}%`} />
                <MetricCard label="GPU" value={`${runtime.gpu_usage_pct}%`} />
                <MetricCard label="Memory" value={`${runtime.memory_usage_mb}MB`} />
                <MetricCard label="Errors" value={runtime.error_rate < 0.01 ? 'Low' : 'High'} />
              </div>
            )}

            {/* Behavior stats */}
            {behavior && (
              <div>
                <div className="text-[11px] text-text-tertiary mb-1.5 font-medium">Behavior Statistics</div>
                <div className="grid grid-cols-4 gap-1.5">
                  <div className="text-center">
                    <div className="text-[10px] text-text-tertiary">Curiosity</div>
                    <div className="text-xs text-accent font-medium">{(behavior.curiosity_score * 100).toFixed(0)}%</div>
                  </div>
                  <div className="text-center">
                    <div className="text-[10px] text-text-tertiary">Mastery</div>
                    <div className="text-xs text-accent font-medium">{(behavior.mastery_score * 100).toFixed(0)}%</div>
                  </div>
                  <div className="text-center">
                    <div className="text-[10px] text-text-tertiary">Competence</div>
                    <div className="text-xs text-accent font-medium">{(behavior.competence_score * 100).toFixed(0)}%</div>
                  </div>
                  <div className="text-center">
                    <div className="text-[10px] text-text-tertiary">Autonomy</div>
                    <div className="text-xs text-accent font-medium">{(behavior.autonomy_score * 100).toFixed(0)}%</div>
                  </div>
                </div>
                <div className="flex gap-3 mt-2 text-[10px] text-text-tertiary">
                  <span>{behavior.queries_total} queries</span>
                  <span>{behavior.discoveries_total} discoveries</span>
                  <span>{behavior.reflections_total} reflections</span>
                  <span>{behavior.improvements_total} improvements</span>
                </div>
              </div>
            )}

            {/* Model routing */}
            {routing && (
              <div>
                <div className="text-[11px] text-text-tertiary mb-1.5 font-medium">
                  Model Routing <span className="text-accent">({routing.current_model})</span>
                </div>
                <div className="space-y-0">
                  {routing.routing_table.map((decision, i) => (
                    <ModelRoutingRow key={i} decision={decision} />
                  ))}
                </div>
                <div className="flex gap-3 mt-1.5 text-[10px] text-text-tertiary">
                  <span>Avg latency: {routing.avg_latency_ms}ms</span>
                  <span>Fallbacks: {routing.fallback_count}</span>
                </div>
              </div>
            )}
          </div>
        </Panel>
      )}

      {/* ── Evidence ─────────────────────────────────────────────── */}
      {currentStep >= 4 && evidence.length > 0 && (
        <Panel title="Evidence Acquired">
          <div className="space-y-2">
            {evidence.map((doc, i) => (
              <div key={i} className="p-2 rounded bg-surface-2 text-xs space-y-1">
                <div className="flex items-center justify-between">
                  <span className="text-text-secondary font-medium truncate">{String(doc.title)}</span>
                  <span className="text-2xs text-accent shrink-0 ml-2">{((doc.confidence as number) * 100).toFixed(0)}%</span>
                </div>
                <div className="text-text-tertiary text-[11px]">{String(doc.source)} — {String(doc.author)}</div>
                <div className="text-text-secondary text-[11px] leading-relaxed">{String(doc.summary)}</div>
              </div>
            ))}
          </div>
        </Panel>
      )}

      {/* ── Knowledge graph ──────────────────────────────────────── */}
      {currentStep >= 6 && knowledgeGraph.nodes.length > 0 && (
        <Panel title="Knowledge Graph">
          <div className="flex flex-wrap gap-1.5">
            {knowledgeGraph.nodes.map((node) => (
              <span
                key={String(node.id)}
                className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] bg-surface-2 text-text-secondary border border-border-subtle"
              >
                {String(node.name)}
                <span className="text-text-tertiary">({String(node.connections)})</span>
              </span>
            ))}
          </div>
          <div className="mt-2 text-2xs text-text-tertiary">
            {knowledgeGraph.nodes.length} concepts, {knowledgeGraph.edges.length} relations
          </div>
        </Panel>
      )}

      {/* ── Reflection ───────────────────────────────────────────── */}
      {currentStep >= 7 && reflection && (
        <Panel title="Reflection">
          <div className="space-y-2 text-xs">
            <div>
              <span className="text-text-tertiary">What worked: </span>
              <span className="text-text-secondary">{reflection.what_worked}</span>
            </div>
            <div>
              <span className="text-text-tertiary">Gap: </span>
              <span className="text-text-secondary">{reflection.what_failed}</span>
            </div>
            <div>
              <span className="text-text-tertiary">Lesson: </span>
              <span className="text-text-secondary">{reflection.lesson}</span>
            </div>
          </div>
        </Panel>
      )}

      {/* ── Maldoror proposal ────────────────────────────────────── */}
      {currentStep >= 8 && maldoror && (
        <Panel title="Maldoror Proposal (Dry-Run)">
          <div className="space-y-2 text-xs">
            <div className="flex items-center gap-2">
              <FileText className="w-3.5 h-3.5 text-accent" />
              <span className="text-text-secondary font-medium">{maldoror.description}</span>
            </div>
            <div className="text-text-tertiary">{maldoror.reasoning}</div>
            <div className="flex gap-2 mt-1">
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] bg-status-success/10 text-status-success">
                <CheckCircle2 className="w-3 h-3" /> Syntax valid
              </span>
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] bg-status-success/10 text-status-success">
                <CheckCircle2 className="w-3 h-3" /> Import safe
              </span>
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] bg-status-success/10 text-status-success">
                <CheckCircle2 className="w-3 h-3" /> Sandbox passed
              </span>
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] bg-text-tertiary/10 text-text-tertiary">
                Not applied
              </span>
            </div>
            {maldoror.dry_run_diff && (
              <pre className="mt-2 p-2 rounded bg-surface-2 text-[10px] text-text-secondary overflow-x-auto font-mono leading-relaxed">
                {maldoror.dry_run_diff}
              </pre>
            )}
          </div>
        </Panel>
      )}

      {/* ── Session summary ──────────────────────────────────────── */}
      {isFinal && (
        <Panel title="Session Summary" accentGlow>
          <div className="space-y-2 text-xs">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-status-success" />
              <span className="text-text-secondary font-medium">Demo complete — all stages executed successfully</span>
            </div>
            <div className="grid grid-cols-2 gap-2 mt-2">
              <MetricCard label="Evidence" value={`${evidence.length} sources`} />
              <MetricCard label="Memory" value={`${demo?.memoryWrites || 0} writes`} />
              <MetricCard label="KG Nodes" value={`${knowledgeGraph.nodes.length}`} />
              <MetricCard label="KG Edges" value={`${knowledgeGraph.edges.length}`} />
            </div>
            <div className="mt-2 text-text-tertiary">
              This session used controlled demonstration fixtures. No live model calls were made.
            </div>
          </div>
        </Panel>
      )}
    </div>
  );
}

const DEMO_STEP_NAMES = [
  'System Initialization',
  'Goal Received',
  'Plan Generated',
  'Evidence Acquired',
  'Evidence Validated',
  'Memory Updated',
  'Reflection Complete',
  'Maldoror Pipeline',
  'Demo Complete',
];

const STEP_ICONS = [
  Cpu,
  Target,
  Layers,
  Workflow,
  CheckCircle2,
  Database,
  Eye,
  Zap,
  CheckCircle2,
];

import { useState, useEffect, useCallback } from 'react';
import { Panel, MetricCard } from './Panel';
import { cn } from '@/lib/utils';
import type { AgentStatus, DemoStats } from '@/types';
import {
  Play,
  Pause,
  RotateCcw,
  ChevronRight,
  CheckCircle2,
  Circle,
  Target,
  Search,
  Database,
  Brain,
  Zap,
  GitBranch,
  FileText,
  ArrowRight,
} from 'lucide-react';

interface DemoPanelProps {
  status: AgentStatus | null;
  send: (type: string, payload?: unknown) => void;
}

const STEP_ICONS = [
  Target,
  Search,
  Search,
  CheckCircle2,
  Database,
  Brain,
  Zap,
  CheckCircle2,
];

export function DemoPanel({ status, send }: DemoPanelProps) {
  const demo = status?.demo;
  const [autoPlay, setAutoPlay] = useState(false);
  const [evidence, setEvidence] = useState<unknown[]>([]);
  const [reflection, setReflection] = useState<unknown>(null);
  const [maldoror, setMaldoror] = useState<unknown>(null);
  const [knowledgeGraph, setKnowledgeGraph] = useState<{ nodes: unknown[]; edges: unknown[] }>({ nodes: [], edges: [] });

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
    const timer = setTimeout(advance, 2000);
    return () => clearTimeout(timer);
  }, [autoPlay, demo?.active, demo?.step, demo?.totalSteps, advance]);

  useEffect(() => {
    if (!demo?.active) return;
    const port = window.location.port || '8765';
    const base = `http://127.0.0.1:${port}`;

    fetch(`${base}/api/demo/evidence`).then(r => r.json()).then(setEvidence).catch(() => {});
    fetch(`${base}/api/demo/reflection`).then(r => r.json()).then(setReflection).catch(() => {});
    fetch(`${base}/api/demo/maldoror`).then(r => r.json()).then(setMaldoror).catch(() => {});
    fetch(`${base}/api/demo/knowledge-graph`).then(r => r.json()).then(setKnowledgeGraph).catch(() => {});
  }, [demo?.active, demo?.step]);

  if (!demo?.active) {
    return (
      <div className="h-full overflow-y-auto p-4 space-y-4 animate-panel-in">
        <Panel title="Demo Mode" accentGlow>
          <div className="space-y-4">
            <div className="text-sm text-text-secondary leading-relaxed">
              Run a guided demonstration of Ontogeny's integrated cognitive workflow.
              This walkthrough uses controlled demonstration fixtures based on real system outputs.
            </div>
            <div className="text-xs text-text-tertiary space-y-1">
              <div className="font-medium text-text-secondary mb-2">What you'll see:</div>
              <div className="flex items-center gap-2"><ArrowRight className="w-3 h-3 text-accent" /> Goal reception and plan generation</div>
              <div className="flex items-center gap-2"><ArrowRight className="w-3 h-3 text-accent" /> Knowledge acquisition with source scoring</div>
              <div className="flex items-center gap-2"><ArrowRight className="w-3 h-3 text-accent" /> Evidence validation and memory writes</div>
              <div className="flex items-center gap-2"><ArrowRight className="w-3 h-3 text-accent" /> Reflection and self-model update</div>
              <div className="flex items-center gap-2"><ArrowRight className="w-3 h-3 text-accent" /> Maldoror improvement proposal (dry-run)</div>
            </div>
            <div className="flex gap-2">
              <button onClick={start} className="btn-primary-glass flex items-center gap-2">
                <Play className="w-4 h-4" /> Start Demo
              </button>
            </div>
            <div className="text-2xs text-text-tertiary mt-2">
              Controlled demonstration — no live LLM calls, no network requests, no source code modification.
            </div>
          </div>
        </Panel>
      </div>
    );
  }

  const currentStep = demo.step;
  const totalSteps = demo.totalSteps;

  return (
    <div className="h-full overflow-y-auto p-4 space-y-4 animate-panel-in">
      <Panel title="Demo Mode" accentGlow>
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-status-success animate-pulse" />
            <span className="text-xs text-text-secondary">
              Step {currentStep} of {totalSteps}
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
            <button onClick={advance} className="btn-ghost p-1.5" title="Next step" disabled={currentStep >= totalSteps}>
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
            <button onClick={reset} className="btn-ghost p-1.5" title="Reset demo">
              <RotateCcw className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        <div className="w-full bg-surface-2 rounded-full h-1.5 mb-4">
          <div
            className="bg-accent h-1.5 rounded-full transition-all duration-500"
            style={{ width: `${(currentStep / totalSteps) * 100}%` }}
          />
        </div>

        <div className="space-y-1">
          {Array.from({ length: totalSteps }, (_, i) => {
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
                  !isCompleted && !isCurrent && 'text-text-tertiary opacity-50'
                )}
              >
                {isCompleted ? (
                  <CheckCircle2 className="w-3.5 h-3.5 text-status-success shrink-0" />
                ) : (
                  <Icon className={cn('w-3.5 h-3.5 shrink-0', isCurrent ? 'text-accent' : 'text-text-tertiary')} />
                )}
                <span className="truncate">{DEMO_STEP_NAMES[i]}</span>
              </div>
            );
          })}
        </div>
      </Panel>

      {currentStep >= 3 && evidence.length > 0 && (
        <Panel title="Evidence Acquired">
          <div className="space-y-2">
            {evidence.map((doc: any, i: number) => (
              <div key={i} className="p-2 rounded bg-surface-2 text-xs space-y-1">
                <div className="flex items-center justify-between">
                  <span className="text-text-secondary font-medium truncate">{doc.title}</span>
                  <span className="text-2xs text-accent shrink-0 ml-2">{(doc.confidence * 100).toFixed(0)}%</span>
                </div>
                <div className="text-text-tertiary text-[11px]">{doc.source} — {doc.author}</div>
                <div className="text-text-secondary text-[11px] leading-relaxed">{doc.summary}</div>
              </div>
            ))}
          </div>
        </Panel>
      )}

      {currentStep >= 5 && knowledgeGraph.nodes.length > 0 && (
        <Panel title="Knowledge Graph">
          <div className="flex flex-wrap gap-1.5">
            {knowledgeGraph.nodes.map((node: any) => (
              <span
                key={node.id}
                className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] bg-surface-2 text-text-secondary border border-border-subtle"
              >
                {node.name}
                <span className="text-text-tertiary">({node.connections})</span>
              </span>
            ))}
          </div>
          <div className="mt-2 text-2xs text-text-tertiary">
            {knowledgeGraph.nodes.length} concepts, {knowledgeGraph.edges.length} relations
          </div>
        </Panel>
      )}

      {currentStep >= 6 && reflection && (
        <Panel title="Reflection">
          <div className="space-y-2 text-xs">
            <div>
              <span className="text-text-tertiary">What worked: </span>
              <span className="text-text-secondary">{(reflection as any).what_worked}</span>
            </div>
            <div>
              <span className="text-text-tertiary">Gap: </span>
              <span className="text-text-secondary">{(reflection as any).what_failed}</span>
            </div>
            <div>
              <span className="text-text-tertiary">Lesson: </span>
              <span className="text-text-secondary">{(reflection as any).lesson}</span>
            </div>
          </div>
        </Panel>
      )}

      {currentStep >= 7 && maldoror && (
        <Panel title="Maldoror Proposal (Dry-Run)">
          <div className="space-y-2 text-xs">
            <div className="flex items-center gap-2">
              <FileText className="w-3.5 h-3.5 text-accent" />
              <span className="text-text-secondary font-medium">{(maldoror as any).description}</span>
            </div>
            <div className="text-text-tertiary">{(maldoror as any).reasoning}</div>
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
            {(maldoror as any).dry_run_diff && (
              <pre className="mt-2 p-2 rounded bg-surface-2 text-[10px] text-text-secondary overflow-x-auto font-mono leading-relaxed">
                {(maldoror as any).dry_run_diff}
              </pre>
            )}
          </div>
        </Panel>
      )}

      {currentStep >= totalSteps && (
        <Panel title="Session Summary" accentGlow>
          <div className="space-y-2 text-xs">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-status-success" />
              <span className="text-text-secondary font-medium">Demo complete — all steps executed successfully</span>
            </div>
            <div className="grid grid-cols-2 gap-2 mt-2">
              <MetricCard label="Evidence" value={`${evidence.length} sources`} />
              <MetricCard label="Memory" value={`${(status?.demo as any)?.memoryWrites || 0} writes`} />
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
  'Goal Received',
  'Plan Generated',
  'Evidence Acquired',
  'Evidence Validated',
  'Memory Updated',
  'Reflection Complete',
  'Maldoror Proposal',
  'Demo Complete',
];

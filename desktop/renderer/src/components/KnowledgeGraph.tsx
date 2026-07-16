import { Panel } from './Panel';
import type { AgentStatus } from '@/types';

interface KnowledgeGraphProps {
  status: AgentStatus | null;
}

export function KnowledgeGraph({ status }: KnowledgeGraphProps) {
  const knowledge = status?.knowledge || { nodes: 0, edges: 0 };

  return (
    <div className="h-full overflow-y-auto p-4 space-y-4">
      <Panel title="Knowledge Graph Stats">
        <div className="grid grid-cols-2 gap-3">
          <div className="metric-card">
            <div className="metric-label">Concepts</div>
            <div className="metric-value">{knowledge.nodes}</div>
          </div>
          <div className="metric-card">
            <div className="metric-label">Relations</div>
            <div className="metric-value">{knowledge.edges}</div>
          </div>
        </div>
      </Panel>

      <Panel title="Graph Visualization" className="flex-1">
        <div className="relative w-full h-full min-h-[400px] bg-surface-0 rounded-md overflow-hidden">
          {knowledge.nodes === 0 ? (
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="text-sm text-text-tertiary">No knowledge data</div>
            </div>
          ) : (
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="text-sm text-text-tertiary">
                Graph visualization with {knowledge.nodes} nodes and {knowledge.edges} edges
              </div>
            </div>
          )}
        </div>
      </Panel>

      <Panel title="Recent Concepts">
        <div className="text-sm text-text-tertiary py-4 text-center">
          No recent concepts
        </div>
      </Panel>
    </div>
  );
}

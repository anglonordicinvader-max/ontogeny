import { Panel, MetricCard, ProgressBar } from './Panel';
import type { AgentStatus } from '@/types';

interface CrawlerPanelProps {
  status: AgentStatus | null;
}

export function CrawlerPanel({ status }: CrawlerPanelProps) {
  const crawlers = status?.crawlers || { active: 0, total: 0, requestsToday: 0, bandwidthUsed: 0 };

  return (
    <div className="h-full overflow-y-auto p-4 space-y-4">
      <Panel title="Knowledge Acquisition" accentGlow>
        <div className="grid grid-cols-2 gap-3">
          <MetricCard label="Active Engines" value={crawlers.active} />
          <MetricCard label="Total Engines" value={crawlers.total} />
          <MetricCard label="Requests Today" value={crawlers.requestsToday} />
          <MetricCard label="Bandwidth" value={`${(crawlers.bandwidthUsed / 1024 / 1024).toFixed(1)}MB`} />
        </div>
      </Panel>

      <Panel title="Budget Usage" accentGlow>
        <div className="space-y-3">
          <div className="space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-xs text-text-secondary">Daily Requests</span>
              <span className="text-2xs text-text-tertiary">{crawlers.requestsToday} / 10000</span>
            </div>
            <ProgressBar value={crawlers.requestsToday} max={10000} />
          </div>
          <div className="space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-xs text-text-secondary">Bandwidth</span>
              <span className="text-2xs text-text-tertiary">{(crawlers.bandwidthUsed / 1024 / 1024).toFixed(1)} / 100 MB</span>
            </div>
            <ProgressBar value={crawlers.bandwidthUsed} max={100 * 1024 * 1024} />
          </div>
        </div>
      </Panel>

      <Panel title="Active Sources">
        <div className="text-sm text-text-tertiary py-4 text-center">
          {crawlers.active > 0 ? `${crawlers.active} active acquisition engines` : 'No active acquisition engines'}
        </div>
      </Panel>
    </div>
  );
}

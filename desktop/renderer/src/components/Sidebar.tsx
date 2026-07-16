import { useState } from 'react';
import { cn } from '@/lib/utils';
import {
  Activity,
  Brain,
  Database,
  GitBranch,
  Layout,
  Monitor,
  Settings,
  Target,
  TrendingUp,
  Workflow,
  Cpu,
  Eye,
} from 'lucide-react';

interface SidebarProps {
  activeTab: string;
  onTabChange: (tab: string) => void;
  connected: boolean;
}

const tabs = [
  { id: 'activity', label: 'Activity', icon: Activity },
  { id: 'cognitive', label: 'Cognitive', icon: Brain },
  { id: 'memory', label: 'Memory', icon: Database },
  { id: 'goals', label: 'Goals', icon: Target },
  { id: 'knowledge', label: 'Knowledge', icon: GitBranch },
  { id: 'crawlers', label: 'Crawlers', icon: Workflow },
  { id: 'maldoror', label: 'Maldoror', icon: Cpu },
  { id: 'training', label: 'Training', icon: TrendingUp },
  { id: 'production', label: 'Production', icon: Monitor },
  { id: 'blender', label: 'Sandbox', icon: Eye },
  { id: 'settings', label: 'Settings', icon: Settings },
];

export function Sidebar({ activeTab, onTabChange, connected }: SidebarProps) {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <aside
      className={cn(
        'flex flex-col h-full bg-surface-1 border-r border-border transition-all duration-200',
        collapsed ? 'w-16' : 'w-56'
      )}
    >
      <div className="flex items-center justify-between px-4 py-4 border-b border-border">
        {!collapsed && (
          <div className="flex items-center gap-2">
            <Layout className="w-5 h-5 text-accent" />
            <span className="text-sm font-semibold text-text-primary">Ontogeny</span>
          </div>
        )}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="btn-ghost p-1.5"
        >
          <Layout className="w-4 h-4" />
        </button>
      </div>

      <nav className="flex-1 py-2 overflow-y-auto">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => onTabChange(tab.id)}
              className={cn(
                'sidebar-item',
                isActive && 'active'
              )}
            >
              <Icon className="w-4 h-4 shrink-0" />
              {!collapsed && <span>{tab.label}</span>}
            </button>
          );
        })}
      </nav>

      <div className="px-4 py-3 border-t border-border">
        <div className="flex items-center gap-2">
          <div className={cn('status-dot', connected ? 'status-dot-active' : 'status-dot-error')} />
          {!collapsed && (
            <span className="text-2xs text-text-tertiary">
              {connected ? 'Connected' : 'Disconnected'}
            </span>
          )}
        </div>
      </div>
    </aside>
  );
}

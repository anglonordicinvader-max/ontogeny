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
  Workflow,
  Cpu,
  Eye,
  PanelLeftClose,
  PanelLeftOpen,
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
  { id: 'production', label: 'Production', icon: Monitor },
  { id: 'blender', label: 'Sandbox', icon: Eye },
  { id: 'settings', label: 'Settings', icon: Settings },
];

export function Sidebar({ activeTab, onTabChange, connected }: SidebarProps) {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <aside
      className={cn(
        'flex flex-col h-full border-r border-border transition-all duration-200 ease-out',
        collapsed ? 'w-14' : 'w-52'
      )}
      style={{ background: 'var(--surface-1)' }}
    >
      <div className="flex items-center justify-between px-3 py-3 border-b border-border">
        {!collapsed && (
          <div className="flex items-center gap-2">
            <Layout className="w-4 h-4 text-accent" />
            <span className="text-xs font-semibold text-text-secondary tracking-wide">NAVIGATE</span>
          </div>
        )}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="btn-ghost p-1.5 rounded-md"
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {collapsed ? (
            <PanelLeftOpen className="w-4 h-4 text-text-secondary" />
          ) : (
            <PanelLeftClose className="w-4 h-4 text-text-secondary" />
          )}
        </button>
      </div>

      <nav className="flex-1 py-2 overflow-y-auto" role="navigation" aria-label="Main navigation">
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
              aria-current={isActive ? 'page' : undefined}
              aria-label={tab.label}
              data-tooltip={collapsed ? tab.label : undefined}
            >
              <Icon className="w-4 h-4 shrink-0" />
              {!collapsed && <span>{tab.label}</span>}
            </button>
          );
        })}
      </nav>

      <div className="px-3 py-3 border-t border-border">
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

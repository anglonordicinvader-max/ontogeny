import { useState } from 'react';
import { cn } from '@/lib/utils';
import {
  Activity,
  Brain,
  Database,
  GitBranch,
  Monitor,
  Settings,
  Target,
  Workflow,
  Cpu,
  Eye,
  PanelLeftClose,
  PanelLeftOpen,
  Search,
  Box,
} from 'lucide-react';

interface SidebarProps {
  activeTab: string;
  onTabChange: (tab: string) => void;
  onSearchOpen: () => void;
  connected: boolean;
}

const tabs = [
  { id: 'activity', label: 'Activity', icon: Activity },
  { id: 'cognitive', label: 'Cognitive', icon: Brain },
  { id: 'memory', label: 'Memory', icon: Database },
  { id: 'goals', label: 'Goals', icon: Target },
  { id: 'knowledge', label: 'Knowledge', icon: GitBranch },
  { id: 'crawlers', label: 'Knowledge', icon: Workflow },
  { id: 'maldoror', label: 'Maldoror', icon: Cpu },
  { id: 'production', label: 'Production', icon: Monitor },
  { id: 'blender', label: 'Blender', icon: Eye },
  { id: 'mujoco', label: 'MuJoCo', icon: Box },
  { id: 'settings', label: 'Settings', icon: Settings },
];

export function Sidebar({ activeTab, onTabChange, onSearchOpen, connected }: SidebarProps) {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <aside
      className={cn(
        'flex flex-col h-full border-r transition-all duration-200 ease-out',
        collapsed ? 'w-14' : 'w-52'
      )}
      style={{ background: 'var(--sidebar-bg)', borderColor: 'var(--sidebar-border)' }}
    >
      <div className="flex items-center justify-between px-3 py-3 border-b" style={{ borderColor: 'var(--sidebar-border)' }}>
        {!collapsed && (
          <button
            onClick={onSearchOpen}
            className="flex items-center gap-2 flex-1 px-2 py-1.5 text-xs rounded-md transition-colors hover:bg-white/[0.04]"
            style={{ color: 'var(--sidebar-text-muted)' }}
            aria-label="Open search"
          >
            <Search className="w-3.5 h-3.5" />
            <span>Search</span>
            <span className="ml-auto text-[10px] opacity-40" style={{ fontFamily: "'Geist Mono', monospace" }}>⌘K</span>
          </button>
        )}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="p-1.5 rounded-md transition-colors hover:bg-white/[0.06]"
          style={{ color: 'var(--sidebar-text-muted)' }}
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {collapsed ? (
            <PanelLeftOpen className="w-4 h-4" />
          ) : (
            <PanelLeftClose className="w-4 h-4" />
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

      <div className="px-3 py-3 border-t" style={{ borderColor: 'var(--sidebar-border)' }}>
        <div className="flex items-center gap-2">
          <div className={cn('status-dot', connected ? 'status-dot-active' : 'status-dot-error')} />
          {!collapsed && (
            <span className="text-2xs" style={{ color: 'var(--sidebar-text-muted)' }}>
              {connected ? 'Connected' : 'Disconnected'}
            </span>
          )}
        </div>
      </div>
    </aside>
  );
}

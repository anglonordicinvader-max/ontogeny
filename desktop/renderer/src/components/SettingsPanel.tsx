import { useState, useEffect } from 'react';
import { Panel } from './Panel';
import { APP_VERSION } from '@/types';

interface Settings {
  backendPort: number;
  autoConnect: boolean;
  refreshRate: number;
  theme: 'dark' | 'light';
  notifications: boolean;
  soundEnabled: boolean;
}

const defaultSettings: Settings = {
  backendPort: 8765,
  autoConnect: true,
  refreshRate: 1,
  theme: 'dark',
  notifications: true,
  soundEnabled: false,
};

function applyTheme(theme: 'dark' | 'light') {
  const root = document.documentElement;
  const content = document.getElementById('root');
  if (!content) {
    root.classList.toggle('light', theme === 'light');
    root.classList.toggle('dark', theme !== 'light');
    return;
  }
  content.style.transition = 'opacity 120ms ease-out';
  content.style.opacity = '0.6';
  requestAnimationFrame(() => {
    setTimeout(() => {
      root.classList.toggle('light', theme === 'light');
      root.classList.toggle('dark', theme !== 'light');
      content.style.opacity = '1';
      setTimeout(() => {
        content.style.transition = '';
      }, 200);
    }, 120);
  });
}

export function SettingsPanel() {
  const [settings, setSettings] = useState<Settings>(() => {
    const saved = localStorage.getItem('ontogeny-settings');
    return saved ? { ...defaultSettings, ...JSON.parse(saved) } : defaultSettings;
  });
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    const root = document.documentElement;
    root.classList.toggle('light', settings.theme === 'light');
    root.classList.toggle('dark', settings.theme !== 'light');
  }, []);

  const handleSave = () => {
    localStorage.setItem('ontogeny-settings', JSON.stringify(settings));
    applyTheme(settings.theme);
    setSaved(true);
    setTimeout(() => setSaved(false), 1800);
  };

  const handleChange = (key: keyof Settings, value: unknown) => {
    setSettings((prev) => ({ ...prev, [key]: value }));
    if (key === 'theme') {
      applyTheme(value as 'dark' | 'light');
    }
  };

  const sliderFillPct = ((settings.refreshRate - 0.5) / (5 - 0.5)) * 100;

  return (
    <div className="h-full overflow-y-auto p-4 space-y-4 animate-panel-in">
      <Panel title="Backend Configuration" accentGlow>
        <div className="space-y-4">
          <div className="space-y-2">
            <label className="text-xs text-text-secondary">Backend Port</label>
            <input
              type="number"
              value={settings.backendPort}
              onChange={(e) => handleChange('backendPort', parseInt(e.target.value))}
              className="w-full px-3 py-2 bg-surface-2 border border-border rounded-md text-sm text-text-primary focus:outline-none focus:border-accent transition-colors"
            />
          </div>
          <div className="flex items-center justify-between">
            <span className="text-xs text-text-secondary">Auto-connect on startup</span>
            <button
              onClick={() => handleChange('autoConnect', !settings.autoConnect)}
              aria-label="Toggle auto-connect"
              role="switch"
              aria-checked={settings.autoConnect}
              className="relative w-10 h-5 rounded-full transition-all duration-200"
              style={{
                background: settings.autoConnect ? 'var(--accent-glass)' : 'var(--surface-4)',
                backdropFilter: settings.autoConnect ? 'blur(6px)' : 'none',
                boxShadow: settings.autoConnect ? '0 0 14px 2px var(--bloom-color)' : 'none',
              }}
            >
              <div
                className="w-4 h-4 rounded-full bg-white shadow-sm transform transition-transform duration-200"
                style={{ transform: settings.autoConnect ? 'translateX(20px)' : 'translateX(2px)' }}
              />
            </button>
          </div>
        </div>
      </Panel>

      <Panel title="Display" accentGlow>
        <div className="space-y-4">
          <div className="space-y-2">
            <label className="text-xs text-text-secondary">Refresh Rate (seconds)</label>
            <div className="slider-wrapper">
              <div className="slider-track" />
              <div className="slider-fill" style={{ width: `${sliderFillPct}%` }} />
              <input
                type="range"
                min="0.5"
                max="5"
                step="0.5"
                value={settings.refreshRate}
                onChange={(e) => handleChange('refreshRate', parseFloat(e.target.value))}
                className="accent-slider"
              />
            </div>
            <div className="text-2xs text-text-tertiary text-right">{settings.refreshRate}s</div>
          </div>
          <div className="space-y-2">
            <label className="text-xs text-text-secondary">Theme</label>
            <div className="flex gap-2">
              <button
                onClick={() => handleChange('theme', 'dark')}
                className="flex-1 px-3 py-2 rounded-md text-sm border transition-all duration-200"
                style={{
                  borderColor: settings.theme === 'dark' ? 'var(--accent)' : 'var(--border)',
                  color: settings.theme === 'dark' ? 'var(--text-primary)' : 'var(--text-secondary)',
                  background: settings.theme === 'dark' ? 'var(--accent-glass-light)' : 'var(--surface-2)',
                  backdropFilter: settings.theme === 'dark' ? 'blur(6px)' : 'none',
                  boxShadow: settings.theme === 'dark' ? '0 0 14px 2px var(--bloom-color)' : 'none',
                }}
              >
                Dark
              </button>
              <button
                onClick={() => handleChange('theme', 'light')}
                className="flex-1 px-3 py-2 rounded-md text-sm border transition-all duration-200"
                style={{
                  borderColor: settings.theme === 'light' ? 'var(--accent)' : 'var(--border)',
                  color: settings.theme === 'light' ? 'var(--text-primary)' : 'var(--text-secondary)',
                  background: settings.theme === 'light' ? 'var(--accent-glass-light)' : 'var(--surface-2)',
                  backdropFilter: settings.theme === 'light' ? 'blur(6px)' : 'none',
                  boxShadow: settings.theme === 'light' ? '0 0 14px 2px var(--bloom-color)' : 'none',
                }}
              >
                Light
              </button>
            </div>
          </div>
        </div>
      </Panel>

      <Panel title="Notifications" accentGlow>
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-xs text-text-secondary">Enable notifications</span>
            <button
              onClick={() => handleChange('notifications', !settings.notifications)}
              aria-label="Toggle notifications"
              role="switch"
              aria-checked={settings.notifications}
              className="relative w-10 h-5 rounded-full transition-all duration-200"
              style={{
                background: settings.notifications ? 'var(--accent-glass)' : 'var(--surface-4)',
                backdropFilter: settings.notifications ? 'blur(6px)' : 'none',
                boxShadow: settings.notifications ? '0 0 14px 2px var(--bloom-color)' : 'none',
              }}
            >
              <div
                className="w-4 h-4 rounded-full bg-white shadow-sm transform transition-transform duration-200"
                style={{ transform: settings.notifications ? 'translateX(20px)' : 'translateX(2px)' }}
              />
            </button>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-xs text-text-secondary">Sound effects</span>
            <button
              onClick={() => handleChange('soundEnabled', !settings.soundEnabled)}
              aria-label="Toggle sound effects"
              role="switch"
              aria-checked={settings.soundEnabled}
              className="relative w-10 h-5 rounded-full transition-all duration-200"
              style={{
                background: settings.soundEnabled ? 'var(--accent-glass)' : 'var(--surface-4)',
                backdropFilter: settings.soundEnabled ? 'blur(6px)' : 'none',
                boxShadow: settings.soundEnabled ? '0 0 14px 2px var(--bloom-color)' : 'none',
              }}
            >
              <div
                className="w-4 h-4 rounded-full bg-white shadow-sm transform transition-transform duration-200"
                style={{ transform: settings.soundEnabled ? 'translateX(20px)' : 'translateX(2px)' }}
              />
            </button>
          </div>
        </div>
      </Panel>

      <Panel title="About">
        <div className="space-y-2">
          <div className="text-xs text-text-secondary font-medium">Ontogeny v{APP_VERSION}</div>
          <div className="text-2xs text-text-tertiary">Proto-AGI Research Workstation</div>
          <div className="text-2xs text-text-tertiary">License: AGPL-3.0</div>
        </div>
      </Panel>

      <div className="flex items-center gap-3">
        <button onClick={handleSave} className="btn-primary-glass">
          Save Settings
        </button>
        {saved && (
          <span className="text-xs text-status-success animate-fade-out-delayed">
            Settings saved
          </span>
        )}
      </div>
    </div>
  );
}

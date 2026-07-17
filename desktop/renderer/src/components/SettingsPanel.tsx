import { useState, useEffect } from 'react';
import { Panel } from './Panel';

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
  root.classList.add('theme-transitioning');
  root.classList.toggle('light', theme === 'light');
  root.classList.toggle('dark', theme !== 'light');
  setTimeout(() => root.classList.remove('theme-transitioning'), 350);
}

export function SettingsPanel() {
  const [settings, setSettings] = useState<Settings>(() => {
    const saved = localStorage.getItem('ontogeny-settings');
    return saved ? { ...defaultSettings, ...JSON.parse(saved) } : defaultSettings;
  });
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    applyTheme(settings.theme);
  }, []);

  const handleSave = () => {
    localStorage.setItem('ontogeny-settings', JSON.stringify(settings));
    applyTheme(settings.theme);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const handleChange = (key: keyof Settings, value: unknown) => {
    setSettings((prev) => ({ ...prev, [key]: value }));
    if (key === 'theme') {
      applyTheme(value as 'dark' | 'light');
    }
  };

  return (
    <div className="h-full overflow-y-auto p-4 space-y-4 animate-panel-in">
      <Panel title="Backend Configuration">
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
              className={`w-10 h-5 rounded-full transition-colors ${
                settings.autoConnect ? 'bg-accent' : 'bg-surface-3'
              }`}
            >
              <div
                className={`w-4 h-4 rounded-full bg-white transform transition-transform ${
                  settings.autoConnect ? 'translate-x-5' : 'translate-x-0.5'
                }`}
              />
            </button>
          </div>
        </div>
      </Panel>

      <Panel title="Display">
        <div className="space-y-4">
          <div className="space-y-2">
            <label className="text-xs text-text-secondary">Refresh Rate (seconds)</label>
            <input
              type="range"
              min="0.5"
              max="5"
              step="0.5"
              value={settings.refreshRate}
              onChange={(e) => handleChange('refreshRate', parseFloat(e.target.value))}
              className="w-full"
            />
            <div className="text-2xs text-text-tertiary text-right">{settings.refreshRate}s</div>
          </div>
          <div className="space-y-2">
            <label className="text-xs text-text-secondary">Theme</label>
            <div className="flex gap-2">
              <button
                onClick={() => handleChange('theme', 'dark')}
                className={`flex-1 px-3 py-2 rounded-md text-sm border transition-colors ${
                  settings.theme === 'dark'
                    ? 'bg-surface-3 border-accent text-text-primary'
                    : 'bg-surface-2 border-border text-text-secondary hover:border-border-emphasis'
                }`}
              >
                Dark
              </button>
              <button
                onClick={() => handleChange('theme', 'light')}
                className={`flex-1 px-3 py-2 rounded-md text-sm border transition-colors ${
                  settings.theme === 'light'
                    ? 'bg-surface-3 border-accent text-text-primary'
                    : 'bg-surface-2 border-border text-text-secondary hover:border-border-emphasis'
                }`}
              >
                Light
              </button>
            </div>
          </div>
        </div>
      </Panel>

      <Panel title="Notifications">
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-xs text-text-secondary">Enable notifications</span>
            <button
              onClick={() => handleChange('notifications', !settings.notifications)}
              aria-label="Toggle notifications"
              role="switch"
              aria-checked={settings.notifications}
              className={`w-10 h-5 rounded-full transition-colors ${
                settings.notifications ? 'bg-accent' : 'bg-surface-3'
              }`}
            >
              <div
                className={`w-4 h-4 rounded-full bg-white transform transition-transform ${
                  settings.notifications ? 'translate-x-5' : 'translate-x-0.5'
                }`}
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
              className={`w-10 h-5 rounded-full transition-colors ${
                settings.soundEnabled ? 'bg-accent' : 'bg-surface-3'
              }`}
            >
              <div
                className={`w-4 h-4 rounded-full bg-white transform transition-transform ${
                  settings.soundEnabled ? 'translate-x-5' : 'translate-x-0.5'
                }`}
              />
            </button>
          </div>
        </div>
      </Panel>

      <Panel title="About">
        <div className="space-y-2">
          <div className="text-xs text-text-secondary">Ontogeny v1.0.0</div>
          <div className="text-2xs text-text-tertiary">AI-Native Research Workstation</div>
          <div className="text-2xs text-text-tertiary">License: AGPL-3.0</div>
        </div>
      </Panel>

      <div className="flex items-center gap-2">
        <button onClick={handleSave} className="btn-primary">
          Save Settings
        </button>
        {saved && (
          <span className="text-xs text-status-success animate-fade-in">
            Settings saved
          </span>
        )}
      </div>
    </div>
  );
}

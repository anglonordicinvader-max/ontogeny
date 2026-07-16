export {};

declare global {
  interface Window {
    electronAPI?: {
      getBackendPort: () => Promise<number>;
      minimize: () => void;
      maximize: () => void;
      close: () => void;
    };
  }
}

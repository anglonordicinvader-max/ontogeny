export {};

declare global {
  interface Window {
    electronAPI?: {
      getBackendPort: () => Promise<number>;
      getBlenderPort: () => Promise<number>;
      getMuJoCoPort: () => Promise<number>;
      minimize: () => void;
      maximize: () => void;
      close: () => void;
    };
  }
}

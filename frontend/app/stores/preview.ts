import { atom, computed } from "nanostores";

export const $detectedPorts = atom<number[]>([]);
export const $activePort = atom<number | null>(null);

export const $previewUrl = computed([$activePort], (port) => {
  return port ? `http://localhost:${port}` : null;
});

// Parse terminal output for port numbers
const PORT_PATTERNS = [
  /(?:listening|running|started|serving)\s+(?:on|at)\s+(?:https?:\/\/)?(?:localhost|0\.0\.0\.0|127\.0\.0\.1):(\d+)/i,
  /port\s+(\d+)/i,
  /localhost:(\d+)/i,
];

export function detectPorts(output: string) {
  for (const pattern of PORT_PATTERNS) {
    const match = output.match(pattern);
    if (match) {
      const port = parseInt(match[1], 10);
      if (port > 0 && port < 65536) {
        const ports = $detectedPorts.get();
        if (!ports.includes(port)) {
          $detectedPorts.set([...ports, port]);
          if (!$activePort.get()) $activePort.set(port);
        }
      }
    }
  }
}

const RECONNECT_DELAY = 3000;

export class AgentWebSocket {
  private ws: WebSocket | null = null;
  private taskId: string;
  private baseUrl: string;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  public onEvent: ((event: any) => void) | null = null;
  public onClose: (() => void) | null = null;

  constructor(taskId: string, baseUrl = "ws://localhost:8000") {
    this.taskId = taskId;
    this.baseUrl = baseUrl;
  }

  connect() {
    this.ws = new WebSocket(`${this.baseUrl}/ws/${this.taskId}`);
    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        this.onEvent?.(data);
      } catch (e) {
        console.error("Failed to parse WebSocket message:", e);
      }
    };
    this.ws.onclose = (event) => {
      if (event.code !== 1000 && this.reconnectAttempts < this.maxReconnectAttempts) {
        // Abnormal close, try reconnect (don't fire onClose yet)
        this.reconnectAttempts++;
        setTimeout(() => this.connect(), RECONNECT_DELAY);
      } else {
        // Normal close or max retries exceeded — notify caller
        this.onClose?.();
      }
    };
    this.ws.onerror = (error) => {
      console.error("WebSocket error:", error);
    };
  }

  disconnect() {
    if (this.ws) {
      this.ws.close(1000);
      this.ws = null;
    }
  }
}

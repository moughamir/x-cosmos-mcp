import { css, html, LitElement } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { PipelineRun } from '../types/PipelineRun';

@customElement('pipeline-progress')
export class PipelineProgress extends LitElement {
  static styles = css`
    :host {
      display: block;
      padding: 1rem;
    }
    .container {
      max-width: 1200px;
      margin: 0 auto;
    }
    h1 {
      font-size: 2rem;
      font-weight: bold;
      margin-bottom: 1.5rem;
      color: #333;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      margin-top: 1rem;
      box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
      background-color: #fff;
    }
    th,
    td {
      padding: 0.75rem;
      text-align: left;
      border-bottom: 1px solid #e2e8f0;
    }
    th {
      background-color: #f8faff;
      font-weight: 600;
      color: #4a5568;
      text-transform: uppercase;
      font-size: 0.875rem;
    }
    tr:hover {
      background-color: #f0f4f8;
    }
    .status-running {
      color: #f59e0b; /* amber-500 */
      font-weight: 500;
    }
    .status-completed {
      color: #22c55e; /* green-500 */
      font-weight: 500;
    }
    .status-failed {
      color: #ef4444; /* red-500 */
      font-weight: 500;
    }
  `;

  @state()
  private pipelineRuns: PipelineRun[] = [];

  private websocket: WebSocket | null = null;
  private intervalId: number | undefined;

  async connectedCallback() {
    super.connectedCallback();
    this.connectWebSocket();
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    this.disconnectWebSocket();
  }

  connectWebSocket() {
    try {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${window.location.host}/ws/pipeline-progress`;

      this.websocket = new WebSocket(wsUrl);

      this.websocket.onopen = () => {
        console.log('Pipeline progress WebSocket connected');
      };

      this.websocket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (
            data.type === 'initial_data' ||
            data.type === 'pipeline_runs_update' ||
            data.type === 'pipeline_progress_update'
          ) {
            this.pipelineRuns = data.pipeline_runs || [];
            this.requestUpdate();
          }
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

      this.websocket.onerror = (error) => {
        console.error('WebSocket error:', error);
      };

      this.websocket.onclose = () => {
        console.log(
          'WebSocket connection closed, reconnecting in 5 seconds...'
        );
        // Reconnect after 5 seconds if connection is lost
        setTimeout(() => this.connectWebSocket(), 5000);
      };
    } catch (error) {
      console.error('Error connecting to WebSocket:', error);
      // Fallback to polling if WebSocket fails
      this.intervalId = setInterval(() => this.fetchPipelineRuns(), 5000);
    }
  }

  disconnectWebSocket() {
    if (this.intervalId) {
      clearInterval(this.intervalId);
      this.intervalId = undefined;
    }

    if (this.websocket) {
      this.websocket.close();
      this.websocket = null;
    }
  }

  async fetchPipelineRuns() {
    try {
      const response = await fetch('/api/pipeline/runs');
      if (response.ok) {
        this.pipelineRuns = await response.json();
        this.requestUpdate();
      } else {
        console.error('Failed to fetch pipeline runs:', response.statusText);
      }
    } catch (error) {
      console.error('Error fetching pipeline runs:', error);
    }
  }

  render() {
    return html`
      <div class="container">
        <h1>Pipeline Progress</h1>
        ${this.pipelineRuns.length === 0
          ? html`<p>No pipeline runs recorded yet.</p>`
          : html`
              <table>
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Task Type</th>
                    <th>Status</th>
                    <th>Start Time</th>
                    <th>End Time</th>
                    <th>Total Products</th>
                    <th>Processed</th>
                    <th>Failed</th>
                  </tr>
                </thead>
                <tbody>
                  ${this.pipelineRuns.map(
                    (run) => html`
                      <tr>
                        <td>${run.id}</td>
                        <td>${run.task_type}</td>
                        <td>
                          <span class="status-${run.status.toLowerCase()}">
                            ${run.status}
                          </span>
                        </td>
                        <td>${new Date(run.start_time).toLocaleString()}</td>
                        <td>
                          ${run.end_time
                            ? new Date(run.end_time).toLocaleString()
                            : 'N/A'}
                        </td>
                        <td>${run.total_products}</td>
                        <td>${run.processed_products}</td>
                        <td>${run.failed_products}</td>
                      </tr>
                    `
                  )}
                </tbody>
              </table>
            `}
      </div>
    `;
  }
}

import { LitElement, html, css } from 'lit';
import { customElement, state } from 'lit/decorators.js';

interface PipelineRun {
  id: number;
  task_type: string;
  status: string;
  start_time: string;
  end_time: string | null;
  total_products: number;
  processed_products: number;
  failed_products: number;
}

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
      box-shadow: 0 1px 3px rgba(0,0,0,0.1);
      background-color: #fff;
    }
    th, td {
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

  private intervalId: number | undefined;

  async connectedCallback() {
    super.connectedCallback();
    this.fetchPipelineRuns();
    // Refresh every 5 seconds
    this.intervalId = setInterval(() => this.fetchPipelineRuns(), 5000);
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    if (this.intervalId) {
      clearInterval(this.intervalId);
    }
  }

  async fetchPipelineRuns() {
    try {
      const response = await fetch('/api/pipeline/runs');
      if (response.ok) {
        this.pipelineRuns = await response.json();
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
                      <td>${run.end_time ? new Date(run.end_time).toLocaleString() : 'N/A'}</td>
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

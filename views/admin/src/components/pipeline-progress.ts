import { css, html, LitElement } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { PipelineRun } from '../types/PipelineRun';
import { subscribe } from '../utils/websocket';

@customElement('pipeline-progress')
export class PipelineProgress extends LitElement {
  // ... (styles remain the same)

  @state()
  private pipelineRuns: PipelineRun[] = [];

  private unsubscribe: () => void = () => {};

  override connectedCallback() {
    super.connectedCallback();
    this.unsubscribe = subscribe(data => {
      if (data.type === 'initial_data' || data.type === 'pipeline_runs_update' || data.type === 'pipeline_progress_update') {
        this.pipelineRuns = data.pipeline_runs || [];
      }
    });
  }

  override disconnectedCallback() {
    super.disconnectedCallback();
    this.unsubscribe();
  }

  override render() {
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

import { css, html, LitElement } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { ChangeLogEntry } from '../types/ChangeLogEntry';

@customElement('change-log')
export class ChangeLog extends LitElement {
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
    .product-link {
      color: #3b82f6;
      text-decoration: none;
      font-weight: 500;
    }
    .product-link:hover {
      text-decoration: underline;
    }
    .reviewed-status {
      font-weight: 500;
    }
    .reviewed-status.yes {
      color: #22c55e; /* green-500 */
    }
    .reviewed-status.no {
      color: #ef4444; /* red-500 */
    }
  `;

  @state()
  private changes: ChangeLogEntry[] = [];

  override async connectedCallback() {
    super.connectedCallback();
    this.fetchChangeLog();
  }

  override render() {

  async fetchChangeLog() {
    try {
      const response = await fetch('/api/changes');
      if (response.ok) {
        this.changes = await response.json();
      } else {
        console.error('Failed to fetch change log:', response.statusText);
      }
    } catch (error) {
      console.error('Error fetching change log:', error);
    }
  }

  render() {
    return html`
      <div class="container">
        <h1>Recent Changes</h1>
        ${this.changes.length === 0
          ? html`<p>No changes recorded yet.</p>`
          : html`
              <table>
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Product ID</th>
                    <th>Field</th>
                    <th>Old Value</th>
                    <th>New Value</th>
                    <th>Source</th>
                    <th>Date</th>
                    <th>Reviewed</th>
                  </tr>
                </thead>
                <tbody>
                  ${this.changes.map(
                    (change) => html`
                      <tr>
                        <td>${change.id}</td>
                        <td>
                          <a
                            href="/products/${change.product_id}"
                            class="product-link"
                            >${change.product_id}</a
                          >
                        </td>
                        <td>${change.field}</td>
                        <td>
                          ${change.old.length > 50
                            ? `${change.old.substring(0, 50)}...`
                            : change.old}
                        </td>
                        <td>
                          ${change.new.length > 50
                            ? `${change.new.substring(0, 50)}...`
                            : change.new}
                        </td>
                        <td>${change.source}</td>
                        <td>${new Date(change.created_at).toLocaleString()}</td>
                        <td>
                          <span
                            class="reviewed-status ${change.reviewed
                              ? 'yes'
                              : 'no'}">
                            ${change.reviewed ? 'Yes' : 'No'}
                          </span>
                        </td>
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

import { css, html, LitElement } from "lit";
import { customElement, state } from "lit/decorators.js";

export interface TableSchema {
	name: string;
	columns: { name: string; type: string }[];
}

@customElement("db-management")
export class DbManagement extends LitElement {
	static styles = css`
    :host {
      display: block;
      padding: 1rem;
    }
    .schema-display {
      background-color: #f4f4f4;
      border: 1px solid #ddd;
      padding: 1rem;
      margin-bottom: 1rem;
      border-radius: 0.25rem;
      white-space: pre-wrap;
      font-family: monospace;
    }
    .migrate-button {
      background-color: #ef4444; /* red-500 */
      color: white;
      font-weight: bold;
      padding: 0.75rem 1.5rem;
      border-radius: 0.25rem;
      transition: background-color 0.2s;
      cursor: pointer;
    }
    .migrate-button:hover {
      background-color: #dc2626; /* red-700 */
    }
    .refresh-button {
      background-color: #60a5fa; /* blue-400 */
      color: white;
      font-weight: bold;
      padding: 0.5rem 1rem;
      border-radius: 0.25rem;
      transition: background-color 0.2s;
      cursor: pointer;
      margin-bottom: 1rem;
      margin-right: 0.5rem;
    }
    .refresh-button:hover {
      background-color: #3b82f6; /* blue-500 */
    }
  `;

	@state()
	private dbSchema: TableSchema[] = [];

	async connectedCallback() {
		super.connectedCallback();
		this.fetchDbSchema();
	}

	async fetchDbSchema() {
		try {
			const response = await fetch("/api/db/schema");
			this.dbSchema = await response.json();
		} catch (error) {
			console.error("Error fetching DB schema:", error);
		}
	}

	async runMigrations() {
		if (
			!confirm(
				"Are you sure you want to run database migrations? This can alter your database schema.",
			)
		) {
			return;
		}
		try {
			const response = await fetch("/api/db/migrate", {
				method: "POST",
				headers: {
					"Content-Type": "application/json",
				},
			});
			if (response.ok) {
				const result = await response.json();
				alert(`Migrations run successfully: ${result.message}`);
				this.fetchDbSchema(); // Refresh schema after migration
			} else {
				alert("Failed to run migrations.");
			}
		} catch (error) {
			console.error("Error running migrations:", error);
			alert("Error running migrations.");
		}
	}

	render() {
		return html`
      <div class="container mx-auto p-4">
        <h1 class="text-2xl font-bold mb-4">Database Management</h1>

        <div class="mb-4">
          <button @click="${this.fetchDbSchema}" class="refresh-button">
            Refresh Schema
          </button>
          <button @click="${this.runMigrations}" class="migrate-button">
            Run Migrations
          </button>
        </div>

        <h2 class="text-xl font-bold mb-2">Current Schema</h2>
        ${
					this.dbSchema.length === 0
						? html`<p>No schema information available.</p>`
						: html`
              ${this.dbSchema.map(
								(table) => html`
                  <div class="schema-display mb-4">
                    <h3>Table: <strong>${table.name}</strong></h3>
                    <ul>
                      ${table.columns.map(
												(col) => html`<li>${col.name} (${col.type})</li>`,
											)}
                    </ul>
                  </div>
                `,
							)}
            `
				}
      </div>
    `;
	}
}

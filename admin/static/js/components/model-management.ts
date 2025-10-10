import { css, html, LitElement } from "lit";
import { customElement, state } from "lit/decorators.js";

export interface OllamaModel {
	name: string;
	size: number;
	modified_at: string;
}

@customElement("model-management")
export class ModelManagement extends LitElement {
	static styles = css`
    :host {
      display: block;
      padding: 1rem;
    }
    .model-card {
      border: 1px solid #eee;
      padding: 1rem;
      margin-bottom: 1rem;
      border-radius: 0.25rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .pull-button {
      background-color: #10b981; /* green-500 */
      color: white;
      font-weight: bold;
      padding: 0.5rem 1rem;
      border-radius: 0.25rem;
      transition: background-color 0.2s;
      cursor: pointer;
    }
    .pull-button:hover {
      background-color: #059669; /* green-700 */
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
    }
    .refresh-button:hover {
      background-color: #3b82f6; /* blue-500 */
    }
    .input-group {
      display: flex;
      gap: 0.5rem;
      margin-bottom: 1rem;
    }
    input[type="text"] {
      flex-grow: 1;
      padding: 0.5rem;
      border: 1px solid #ccc;
      border-radius: 0.25rem;
    }
  `;

	@state()
	private models: OllamaModel[] = [];

	@state()
	private modelToPull: string = "";

	async connectedCallback() {
		super.connectedCallback();
		this.fetchModels();
	}

	async fetchModels() {
		try {
			const response = await fetch("/api/ollama/models");
			this.models = await response.json();
		} catch (error) {
			console.error("Error fetching Ollama models:", error);
		}
	}

	handleInputChange(e: Event) {
		this.modelToPull = (e.target as HTMLInputElement).value;
	}

	async pullModel() {
		if (!this.modelToPull) return;
		try {
			const response = await fetch("/api/ollama/pull", {
				method: "POST",
				headers: {
					"Content-Type": "application/json",
				},
				body: JSON.stringify({ model_name: this.modelToPull }),
			});
			if (response.ok) {
				alert(`Model ${this.modelToPull} pull initiated.`);
				this.modelToPull = ""; // Clear input
				this.fetchModels(); // Refresh list
			} else {
				alert(`Failed to initiate pull for ${this.modelToPull}.`);
			}
		} catch (error) {
			console.error("Error pulling model:", error);
			alert("Error pulling model.");
		}
	}

	render() {
		return html`
      <div class="container mx-auto p-4">
        <h1 class="text-2xl font-bold mb-4">Ollama Model Management</h1>

        <div class="input-group">
          <input
            type="text"
            placeholder="Enter model name to pull (e.g., llama2)"
            .value="${this.modelToPull}"
            @input="${this.handleInputChange}"
          />
          <button @click="${this.pullModel}" class="pull-button">
            Pull Model
          </button>
        </div>

        <button @click="${this.fetchModels}" class="refresh-button">
          Refresh Models
        </button>

        <div class="model-list">
          ${
						this.models.length === 0
							? html`<p>
                No Ollama models found. Ensure Ollama is running and models are
                pulled.
              </p>`
							: html`
                ${this.models.map(
									(model) => html`
                    <div class="model-card">
                      <div>
                        <strong>${model.name}</strong><br />
                        Size: ${(model.size / (1024 * 1024 * 1024)).toFixed(2)}
                        GB<br />
                        Modified:
                        ${new Date(model.modified_at).toLocaleString()}
                      </div>
                    </div>
                  `,
								)}
              `
					}
        </div>
      </div>
    `;
	}
}

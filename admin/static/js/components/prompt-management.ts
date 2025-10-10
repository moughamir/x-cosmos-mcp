import { css, html, LitElement } from "lit";
import { customElement, state } from "lit/decorators.js";

interface PromptFile {
	name: string;
}

interface PromptContent {
	name: string;
	content: string;
}

@customElement("prompt-management")
export class PromptManagement extends LitElement {
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
    .prompt-list {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
      gap: 1rem;
      margin-bottom: 2rem;
    }
    .prompt-item {
      background-color: #f0f4f8;
      padding: 1rem;
      border-radius: 0.5rem;
      cursor: pointer;
      transition: background-color 0.2s ease-in-out;
    }
    .prompt-item:hover {
      background-color: #e2e8f0;
    }
    .prompt-item.selected {
      background-color: #3b82f6;
      color: white;
    }
    .prompt-content-area {
      background-color: #f8fafc;
      border: 1px solid #e2e8f0;
      border-radius: 0.5rem;
      padding: 1rem;
      font-family: monospace;
      white-space: pre-wrap;
      max-height: 500px;
      overflow-y: auto;
    }
  `;

	@state()
	private promptFiles: PromptFile[] = [];

	@state()
	private selectedPrompt: PromptContent | null = null;

	async connectedCallback() {
		super.connectedCallback();
		this.fetchPromptFiles();
	}

	async fetchPromptFiles() {
		try {
			const response = await fetch("/api/prompts");
			if (response.ok) {
				const data = await response.json();
				this.promptFiles = data.prompts.map((name: string) => ({ name }));
			} else {
				console.error("Failed to fetch prompt files:", response.statusText);
			}
		} catch (error) {
			console.error("Error fetching prompt files:", error);
		}
	}

	async selectPrompt(promptName: string) {
		try {
			const response = await fetch(`/api/prompts/${promptName}`);
			if (response.ok) {
				this.selectedPrompt = await response.json();
			} else {
				console.error(
					`Failed to fetch prompt ${promptName}:`,
					response.statusText,
				);
				this.selectedPrompt = null;
			}
		} catch (error) {
			console.error(`Error fetching prompt ${promptName}:`, error);
			this.selectedPrompt = null;
		}
	}

	render() {
		return html`
      <div class="container">
        <h1>Prompt Management</h1>

        <div class="prompt-list">
          ${
						this.promptFiles.length === 0
							? html`<p>No prompt files found.</p>`
							: this.promptFiles.map(
									(prompt) => html`
                  <div
                    class="prompt-item ${this.selectedPrompt?.name === prompt.name ? "selected" : ""}"
                    @click="${() => this.selectPrompt(prompt.name)}"
                  >
                    ${prompt.name}
                  </div>
                `,
								)
					}
        </div>

        ${
					this.selectedPrompt
						? html`
              <h2>${this.selectedPrompt.name} Content</h2>
              <div class="prompt-content-area">
                ${this.selectedPrompt.content}
              </div>
            `
						: html`<p>Select a prompt to view its content.</p>`
				}
      </div>
    `;
	}
}

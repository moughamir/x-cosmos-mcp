import { css, html, LitElement } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { Product } from '../types/Product';

@customElement('pipeline-management')
export class PipelineManagement extends LitElement {
  static styles = css`
    :host {
      display: block;
      padding: 1rem;
    }
    .form-group {
      margin-bottom: 1rem;
    }
    label {
      display: block;
      margin-bottom: 0.5rem;
      font-weight: bold;
    }
    select,
    textarea {
      width: 100%;
      padding: 0.5rem;
      border: 1px solid #ccc;
      border-radius: 0.25rem;
    }
    .run-button {
      background-color: #4f46e5; /* indigo-600 */
      color: white;
      font-weight: bold;
      padding: 0.75rem 1.5rem;
      border-radius: 0.25rem;
      transition: background-color 0.2s;
      cursor: pointer;
    }
    .run-button:hover {
      background-color: #4338ca; /* indigo-700 */
    }
    .product-selector {
      max-height: 200px;
      overflow-y: auto;
      border: 1px solid #ccc;
      border-radius: 0.25rem;
      padding: 0.5rem;
    }
    .product-item {
      display: flex;
      align-items: center;
      margin-bottom: 0.25rem;
    }
    .product-item input {
      margin-right: 0.5rem;
    }
  `;

  @state()
  private taskType: string = 'meta_optimization';

  @state()
  private allProducts: Product[] = [];

  @state()
  private selectedProductIds: Set<number> = new Set();

  override async connectedCallback() {
    super.connectedCallback();
    this.fetchAllProducts();
  }

  override render() {

  async fetchAllProducts() {
    try {
      const response = await fetch('/api/products');
      const products = await response.json();
      this.allProducts = products.map((p: Product) => ({
        id: p.id,
        title: p.title
      }));
    } catch (error) {
      console.error('Error fetching all products:', error);
    }
  }

  handleTaskTypeChange(e: Event) {
    this.taskType = (e.target as HTMLSelectElement).value;
  }

  handleProductSelection(e: Event) {
    const checkbox = e.target as HTMLInputElement;
    const productId = parseInt(checkbox.value, 10);
    if (checkbox.checked) {
      this.selectedProductIds.add(productId);
    } else {
      this.selectedProductIds.delete(productId);
    }
    this.requestUpdate(); // Force re-render to update checkbox states
  }

  async runPipeline() {
    if (!this.taskType) {
      alert('Please select a task type.');
      return;
    }

    const productIdsArray = Array.from(this.selectedProductIds);

    try {
      const response = await fetch('/api/pipeline/run', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          task_type: this.taskType,
          product_ids: productIdsArray
        })
      });
      if (response.ok) {
        const result = await response.json();
        alert(
          `Pipeline run initiated for ${
            this.taskType
          }. Results: ${JSON.stringify(result.results)}`
        );
        this.selectedProductIds.clear(); // Clear selection after run
        this.requestUpdate();
      } else {
        alert('Failed to initiate pipeline run.');
      }
    } catch (error) {
      console.error('Error running pipeline:', error);
      alert('Error running pipeline.');
    }
  }

  render() {
    return html`
      <div class="container mx-auto p-4">
        <h1 class="text-2xl font-bold mb-4">Pipeline Management</h1>

        <div class="form-group">
          <label for="taskType">Select Task Type:</label>
          <select
            id="taskType"
            .value="${this.taskType}"
            @change="${this.handleTaskTypeChange}">
            <option value="meta_optimization">Meta Optimization</option>
            <option value="content_rewriting">Content Rewriting</option>
            <option value="keyword_analysis">Keyword Analysis</option>
            <option value="tag_optimization">Tag Optimization</option>
            <option value="category_normalization">
              Category Normalization
            </option>
          </select>
        </div>

        <div class="form-group">
          <label>Select Products (optional, leave blank to process all):</label>
          <div class="product-selector">
            ${this.allProducts.map(
              (product) => html`
                <div class="product-item">
                  <input
                    type="checkbox"
                    id="product-${product.id}"
                    value="${product.id}"
                    ?checked="${this.selectedProductIds.has(product.id)}"
                    @change="${this.handleProductSelection}" />
                  <label for="product-${product.id}"
                    >${product.title} (ID: ${product.id})</label
                  >
                </div>
              `
            )}
          </div>
        </div>

        <button
          @click="${this.runPipeline}"
          class="run-button">
          Run Pipeline
        </button>
      </div>
    `;
  }
}

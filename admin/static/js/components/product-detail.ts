import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { Router } from '@vaadin/router';

interface Product {
  id: number;
  title: string;
  body_html: string;
  normalized_title: string;
  normalized_body_html: string;
  llm_confidence: number;
  gmc_category_label: string;
  [key: string]: any; // For other potential fields
}

interface ChangeLogEntry {
  id: number;
  field: string;
  old: string;
  new: string;
  created_at: string;
  source: string;
  reviewed: number;
}

@customElement('product-detail')
export class ProductDetail extends LitElement {
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
    input[type="text"],
    textarea {
      width: 100%;
      padding: 0.5rem;
      border: 1px solid #ccc;
      border-radius: 0.25rem;
    }
    button {
      background-color: #3B82F6; /* blue-500 */
      color: white;
      font-weight: bold;
      padding: 0.5rem 1rem;
      border-radius: 0.25rem;
      transition: background-color 0.2s;
      cursor: pointer;
    }
    button:hover {
      background-color: #2563EB; /* blue-700 */
    }
    .changes-log {
      margin-top: 2rem;
      border-top: 1px solid #eee;
      padding-top: 1rem;
    }
    .change-entry {
      background-color: #f9f9f9;
      border: 1px solid #eee;
      padding: 0.75rem;
      margin-bottom: 0.5rem;
      border-radius: 0.25rem;
    }
  `;

  @property({ type: Number })
  productId: number | undefined;

  @state()
  private product: Product | undefined;

  @state()
  private changes: ChangeLogEntry[] = [];

  @state()
  private editedProduct: Partial<Product> = {};

  async connectedCallback() {
    super.connectedCallback();
    // Extract product_id from the URL
    const path = window.location.pathname;
    const parts = path.split('/');
    const id = parseInt(parts[parts.length - 1]);
    if (!isNaN(id)) {
      this.productId = id;
      await this.fetchProductDetails();
    }
  }

  async fetchProductDetails() {
    if (!this.productId) return;
    try {
      const response = await fetch(`/api/products/${this.productId}`);
      const data = await response.json();
      this.product = data.product;
      this.changes = data.changes;
      this.editedProduct = { ...this.product }; // Initialize edited data
    } catch (error) {
      console.error('Error fetching product details:', error);
    }
  }

  handleInputChange(e: Event) {
    const input = e.target as HTMLInputElement | HTMLTextAreaElement;
    this.editedProduct = {
      ...this.editedProduct,
      [input.name]: input.value,
    };
  }

  async saveChanges() {
    if (!this.productId || !this.editedProduct) return;
    try {
      const response = await fetch(`/api/products/${this.productId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(this.editedProduct),
      });
      if (response.ok) {
        alert('Product updated successfully!');
        await this.fetchProductDetails(); // Re-fetch to update UI and changes log
      } else {
        alert('Failed to update product.');
      }
    } catch (error) {
      console.error('Error saving changes:', error);
      alert('Error saving changes.');
    }
  }

  render() {
    if (!this.product) {
      return html`<p>Loading product details...</p>`;
    }

    return html`
      <div class="container mx-auto p-4">
        <h1 class="text-2xl font-bold mb-4">Product Detail: ${this.product.title}</h1>

        <div class="form-group">
          <label for="title">Title</label>
          <input type="text" id="title" name="title" .value="${this.editedProduct.title || ''}" @input="${this.handleInputChange}">
        </div>
        <div class="form-group">
          <label for="body_html">Body HTML</label>
          <textarea id="body_html" name="body_html" .value="${this.editedProduct.body_html || ''}" @input="${this.handleInputChange}"></textarea>
        </div>
        <div class="form-group">
          <label for="normalized_title">Normalized Title</label>
          <input type="text" id="normalized_title" name="normalized_title" .value="${this.editedProduct.normalized_title || ''}" @input="${this.handleInputChange}">
        </div>
        <div class="form-group">
          <label for="normalized_body_html">Normalized Body HTML</label>
          <textarea id="normalized_body_html" name="normalized_body_html" .value="${this.editedProduct.normalized_body_html || ''}" @input="${this.handleInputChange}"></textarea>
        </div>
        <div class="form-group">
          <label for="gmc_category_label">GMC Category Label</label>
          <input type="text" id="gmc_category_label" name="gmc_category_label" .value="${this.editedProduct.gmc_category_label || ''}" @input="${this.handleInputChange}">
        </div>
        <div class="form-group">
          <label for="llm_confidence">LLM Confidence</label>
          <input type="text" id="llm_confidence" name="llm_confidence" .value="${this.editedProduct.llm_confidence || ''}" @input="${this.handleInputChange}">
        </div>

        <button @click="${this.saveChanges}">Save Changes</button>

        <div class="changes-log">
          <h2 class="text-xl font-bold mb-2">Change Log</h2>
          ${this.changes.length === 0
            ? html`<p>No changes recorded for this product.</p>`
            : html`
                ${this.changes.map(
                  (change) => html`
                    <div class="change-entry">
                      <p><strong>Field:</strong> ${change.field}</p>
                      <p><strong>Old Value:</strong> ${change.old}</p>
                      <p><strong>New Value:</strong> ${change.new}</p>
                      <p><strong>Source:</strong> ${change.source}</p>
                      <p><strong>Date:</strong> ${new Date(change.created_at).toLocaleString()}</p>
                      <p><strong>Reviewed:</strong> ${change.reviewed ? 'Yes' : 'No'}</p>
                    </div>
                  `
                )}
              `}
        </div>
      </div>
    `;
  }
}

import { LitElement, html, css } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { Router } from '@vaadin/router';

interface Product {
  id: number;
  title: string;
  llm_confidence: number;
  gmc_category_label: string;
}

@customElement('product-list')
export class ProductList extends LitElement {
  static styles = css`
    :host {
      display: block;
    }
    .view-button {
      background-color: #3B82F6; /* blue-500 */
      color: white;
      font-weight: bold;
      padding: 0.5rem 1rem;
      border-radius: 0.25rem;
      transition: background-color 0.2s;
    }
    .view-button:hover {
      background-color: #2563EB; /* blue-700 */
    }
  `;

  @state()
  private products: Product[] = [];

  async connectedCallback() {
    super.connectedCallback();
    try {
      const response = await fetch('/api/products');
      this.products = await response.json();
    } catch (error) {
      console.error('Error fetching products:', error);
    }
  }

  navigateToProductDetail(productId: number) {
    Router.go(`/products/${productId}`);
  }

  render() {
    return html`
      <div class="container mx-auto p-4">
        <h1 class="text-2xl font-bold mb-4">Products</h1>
        <table class="min-w-full bg-white">
          <thead>
            <tr>
              <th class="py-2 px-4 border-b">ID</th>
              <th class="py-2 px-4 border-b">Title</th>
              <th class="py-2 px-4 border-b">Confidence</th>
              <th class="py-2 px-4 border-b">Category</th>
              <th class="py-2 px-4 border-b">Actions</th>
            </tr>
          </thead>
          <tbody>
            ${this.products.map(
              (product) => html`
                <tr>
                  <td class="py-2 px-4 border-b">${product.id}</td>
                  <td class="py-2 px-4 border-b">${product.title}</td>
                  <td class="py-2 px-4 border-b">${product.llm_confidence.toFixed(2)}</td>
                  <td class="py-2 px-4 border-b">${product.gmc_category_label}</td>
                  <td class="py-2 px-4 border-b">
                    <button 
                      @click="${() => this.navigateToProductDetail(product.id)}"
                      class="view-button"
                    >View</button>
                  </td>
                </tr>
              `
            )}
          </tbody>
        </table>
      </div>
    `;
  }
}

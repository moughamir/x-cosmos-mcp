import { Router } from "@vaadin/router";
import { css, html, LitElement } from "lit";
import { customElement, state } from "lit/decorators.js";

export interface Product {
	id: number;
	title: string;
	llm_confidence: number;
	gmc_category_label: string;
}

@customElement("product-list")
export class ProductList extends LitElement {
	static styles = css`
    :host {
      display: block;
    }
  `;

	@state()
	private products: Product[] = [];

	async connectedCallback() {
		super.connectedCallback();
		try {
			const response = await fetch("/api/products");
			this.products = await response.json();
		} catch (error) {
			console.error("Error fetching products:", error);
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
                  <td class="py-2 px-4 border-b">
                    ${product.llm_confidence.toFixed(2)}
                  </td>
                  <td class="py-2 px-4 border-b">
                    ${product.gmc_category_label}
                  </td>
                  <td class="py-2 px-4 border-b">
                    <button
                      @click="${() => this.navigateToProductDetail(product.id)}"
                      class="px-3 py-1 bg-blue-500 hover:bg-blue-700 text-white text-sm rounded transition-colors"
                    >
                      View
                    </button>
                  </td>
                </tr>
              `,
						)}
          </tbody>
        </table>
      </div>
    `;
	}
}

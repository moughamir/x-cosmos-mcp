import { css, html, LitElement } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { TaxonomyNode } from '../types/TaxonomyNode';

@customElement('taxonomy-browser')
export class TaxonomyBrowser extends LitElement {
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
    ul {
      list-style: none;
      padding-left: 1.5rem;
    }
    li {
      margin-bottom: 0.5rem;
    }
    .category-item {
      cursor: pointer;
      font-weight: 500;
      color: #2d3748; /* gray-800 */
    }
    .category-item:hover {
      color: #3b82f6; /* blue-500 */
    }
    .full-path {
      font-size: 0.875rem;
      color: #718096; /* gray-500 */
      margin-left: 0.5rem;
    }
    .toggle-icon {
      display: inline-block;
      width: 1em;
      text-align: center;
      margin-right: 0.25em;
    }
  `;

  @state()
  private taxonomyTree: { [key: string]: TaxonomyNode } = {};

  @state()
  private expandedNodes: Set<string> = new Set();

  async connectedCallback() {
    super.connectedCallback();
    this.fetchTaxonomyTree();
  }

  async fetchTaxonomyTree() {
    try {
      const response = await fetch('/api/taxonomy/tree');
      if (response.ok) {
        this.taxonomyTree = await response.json();
      } else {
        console.error('Failed to fetch taxonomy tree:', response.statusText);
      }
    } catch (error) {
      console.error('Error fetching taxonomy tree:', error);
    }
  }

  toggleNode(fullPath: string) {
    if (this.expandedNodes.has(fullPath)) {
      this.expandedNodes.delete(fullPath);
    } else {
      this.expandedNodes.add(fullPath);
    }
    this.requestUpdate();
  }

  renderNode(node: TaxonomyNode) {
    const hasChildren = Object.keys(node.children).length > 0;
    const isExpanded = this.expandedNodes.has(node.full_path);

    return html`
      <li>
        <div
          class="category-item"
          @click="${() => this.toggleNode(node.full_path)}">
          ${hasChildren
            ? html`<span class="toggle-icon">${isExpanded ? '▼' : '►'}</span>`
            : html`<span class="toggle-icon"></span>`}
          ${node.name} <span class="full-path">(${node.full_path})</span>
        </div>
        ${isExpanded && hasChildren
          ? html`
              <ul>
                ${Object.values(node.children).map((child): any =>
                  this.renderNode(child)
                )}
              </ul>
            `
          : ''}
      </li>
    `;
  }

  render() {
    return html`
      <div class="container">
        <h1>Google Product Taxonomy Browser</h1>
        ${Object.keys(this.taxonomyTree).length === 0
          ? html`<p>Loading taxonomy tree...</p>`
          : html`
              <ul>
                ${Object.values(this.taxonomyTree).map((rootNode) =>
                  this.renderNode(rootNode)
                )}
              </ul>
            `}
      </div>
    `;
  }
}

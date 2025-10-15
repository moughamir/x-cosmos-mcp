import { Router } from '@vaadin/router';
import { css, html, LitElement } from 'lit';
import { customElement } from 'lit/decorators.js';

// Import components (will be created later)
import './components/db-management';
import './components/model-management';
import './components/pipeline-management';
import './components/product-detail';
import './components/product-list';
import './components/change-log';
import './components/pipeline-progress';
import './components/taxonomy-browser';
import './components/prompt-management';

@customElement('mcp-admin')
export class McpAdmin extends LitElement {
  static styles = css`
    :host {
      display: flex;
      flex-direction: column;
      min-height: 100vh;
      font-family: system-ui, -apple-system, sans-serif;
    }

    .header {
      background-color: #0f172a; /* slate-900 */
      color: white;
      padding: 1rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .header h1 {
      font-size: 1.25rem; /* text-xl */
      font-weight: 700; /* font-bold */
    }

    .nav {
      display: flex;
      gap: 1rem; /* gap-4 */
    }

    .nav-link {
      padding: 0.5rem 0.75rem; /* px-3 py-2 */
      border-radius: 0.375rem; /* rounded-md */
      background-color: #1e293b; /* slate-800 */
      color: white;
      text-decoration: none;
      transition: background-color 0.15s ease-in-out; /* transition-colors */
    }

    .nav-link:hover {
      background-color: #334155; /* slate-700 */
    }

    .main-content {
      flex: 1;
      padding: 1rem; /* p-4 */
      background-color: #f8fafc; /* slate-50 */
    }
  `;

  firstUpdated() {
    const router = new Router(this.shadowRoot?.querySelector('#outlet'));
    router.setRoutes([
      { path: '/', component: 'product-list' },
      { path: '/products', component: 'product-list' },
      { path: '/products/:id', component: 'product-detail' },
      { path: '/models', component: 'model-management' },
      { path: '/pipeline', component: 'pipeline-management' },
      { path: '/database', component: 'db-management' },
      { path: '/changes', component: 'change-log' },
      { path: '/pipeline-progress', component: 'pipeline-progress' },
      { path: '/taxonomy', component: 'taxonomy-browser' },
      { path: '/prompts', component: 'prompt-management' }
    ]);
  }

  render() {
    return html`
      <header class="header">
        <h1>MCP</h1>
        <nav class="nav">
          <a
            href="/products"
            class="nav-link"
            >Products</a
          >
          <a
            href="/models"
            class="nav-link"
            >Models</a
          >
          <a
            href="/pipeline"
            class="nav-link"
            >Pipeline</a
          >
          <a
            href="/database"
            class="nav-link"
            >Database</a
          >
          <a
            href="/changes"
            class="nav-link"
            >Changes</a
          >
          <a
            href="/pipeline-progress"
            class="nav-link"
            >Progress</a
          >
          <a
            href="/taxonomy"
            class="nav-link"
            >Taxonomy</a
          >
          <a
            href="/prompts"
            class="nav-link"
            >Prompts</a
          >
        </nav>
      </header>
      <main class="main-content">
        <div id="outlet"></div>
      </main>
    `;
  }
}

const appElement = document.getElementById('app');
if (appElement) {
  appElement.innerHTML = '<mcp-admin></mcp-admin>';
}

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

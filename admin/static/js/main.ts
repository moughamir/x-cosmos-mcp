import { LitElement, html, css } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { Router } from '@vaadin/router';

// Import components (will be created later)
import './components/product-list';
import './components/product-detail';
import './components/model-management';
import './components/pipeline-management';
import './components/db-management';

@customElement('mcp-admin')
export class McpAdmin extends LitElement {
  static styles = css`
    :host {
      display: flex;
      flex-direction: column;
      min-height: 100vh;
      font-family: sans-serif;
    }
    .header {
      background-color: #333;
      color: white;
      padding: 1rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .header a {
      color: white;
      text-decoration: none;
      margin-left: 1rem;
    }
    .main-content {
      flex-grow: 1;
      padding: 1rem;
    }
  `;

  @state()
  private currentView: string = 'products';

  firstUpdated() {
    const router = new Router(this.shadowRoot?.querySelector('#outlet'));
    router.setRoutes([
      { path: '/', component: 'product-list' },
      { path: '/products', component: 'product-list' },
      { path: '/products/:id', component: 'product-detail' },
      { path: '/models', component: 'model-management' },
      { path: '/pipeline', component: 'pipeline-management' },
      { path: '/database', component: 'db-management' },
    ]);
  }

  render() {
    return html`
      <header class="header">
        <h1>MCP Admin Panel</h1>
        <nav>
          <a href="/products">Products</a>
          <a href="/models">Models</a>
          <a href="/pipeline">Pipeline</a>
          <a href="/database">Database</a>
        </nav>
      </header>
      <main class="main-content">
        <div id="outlet"></div>
      </main>
    `;
  }
}

document.getElementById('app')!.innerHTML = '<mcp-admin></mcp-admin>';

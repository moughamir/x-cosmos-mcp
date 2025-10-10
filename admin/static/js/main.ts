import { LitElement, html, css } from 'lit';
import { customElement } from 'lit/decorators.js';
import './components/product-list';

@customElement('mcp-admin')
export class McpAdmin extends LitElement {
  static styles = css`
    :host {
      display: block;
    }
  `;

  render() {
    return html`
      <product-list></product-list>
    `;
  }
}

document.getElementById('app')!.innerHTML = '<mcp-admin></mcp-admin>';
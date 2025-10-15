# MCP Admin Frontend Documentation

## Overview

The MCP Admin frontend is a modern, responsive web application built with Lit and TypeScript, providing a comprehensive interface for managing products, database operations, and AI model management.

## Technology Stack

- **Framework:** Lit 3.1.0 (Web Components)
- **Language:** TypeScript 5.3.3
- **Styling:** Tailwind CSS 3.4.1
- **Routing:** Vaadin Router 1.7.5
- **Build Tool:** esbuild 0.19.11

## Application Structure

```
views/admin/
├── src/
│   ├── components/        # Lit components
│   ├── types/            # TypeScript interfaces
│   ├── utils/            # Utility functions
│   ├── main.ts           # Application entry point
│   └── tailwind.css      # Styles
├── static/               # Built assets
│   ├── css/
│   └── js/
└── templates/            # HTML templates
    └── index.html        # Main template
```

---

## Navigation & Routes

The application uses client-side routing with the following routes:

| Route | Component | Description |
|-------|-----------|-------------|
| `/` | ProductList | Default route - shows product list |
| `/products` | ProductList | Browse and search products |
| `/products/:id` | ProductDetail | View/edit specific product |
| `/models` | ModelManagement | Manage Ollama models |
| `/pipeline` | PipelineManagement | Monitor pipeline operations |
| `/database` | DbManagement | Database schema and migrations |
| `/changes` | ChangeLog | View change history |
| `/pipeline-progress` | PipelineProgress | Real-time pipeline monitoring |
| `/taxonomy` | TaxonomyBrowser | Browse product taxonomy |
| `/prompts` | PromptManagement | Manage AI prompts |

---

## Main Features

### 1. Product Management (`/products`)

**Features:**
- Browse all products with pagination
- View product details including change history
- Edit product information inline
- Filter products by confidence scores
- Search functionality (planned)

**Product List View:**
- Displays: ID, Title, Confidence Score, Category, Actions
- Color-coded confidence levels
- Quick access to product details

**Product Detail View:**
- Complete product information display
- Inline editing capabilities
- Change history with before/after values
- Review status tracking

### 2. Model Management (`/models`)

**Features:**
- List all installed Ollama models
- Display model size and modification date
- Pull new models from Ollama registry
- Refresh model list

**Model Information:**
- Model name and version
- File size in GB
- Installation/modification date
- Pull status indicators

### 3. Database Management (`/database`)

**Features:**
- View current database schema
- Display table structures and columns
- Run database migrations
- Schema refresh functionality

**Schema Display:**
- Table names and column definitions
- Data types and constraints
- Row count information (planned)

### 4. Change Log (`/changes`)

**Features:**
- Complete audit trail of all changes
- Filter by product, field, or time period
- Review status tracking
- Change source identification

**Change Information:**
- Product ID and field changed
- Before and after values
- Change source (manual/API/automated)
- Timestamp and review status

### 5. Pipeline Management (`/pipeline`)

**Features:**
- Monitor active pipeline operations
- View pipeline execution history
- Real-time progress tracking
- Error reporting and retry capabilities

### 6. Pipeline Progress (`/pipeline-progress`)

**Features:**
- Real-time pipeline monitoring
- WebSocket-based live updates
- Progress bars and status indicators
- Error alerts and notifications

---

## User Interface

### Navigation

The application features a persistent header navigation with links to all main sections:

```html
<header class="header">
  <h1>MCP</h1>
  <nav class="nav">
    <a href="/products" class="nav-link">Products</a>
    <a href="/models" class="nav-link">Models</a>
    <a href="/pipeline" class="nav-link">Pipeline</a>
    <a href="/database" class="nav-link">Database</a>
    <a href="/changes" class="nav-link">Changes</a>
    <a href="/pipeline-progress" class="nav-link">Progress</a>
    <a href="/taxonomy" class="nav-link">Taxonomy</a>
    <a href="/prompts" class="nav-link">Prompts</a>
  </nav>
</header>
```

### Responsive Design

- **Mobile-friendly:** Responsive layout that works on all screen sizes
- **Tablet optimized:** Touch-friendly interface elements
- **Desktop enhanced:** Full feature utilization on larger screens

### Styling

- **Modern design:** Clean, professional interface using Tailwind CSS
- **Consistent theming:** Unified color scheme and typography
- **Accessibility:** WCAG compliant with proper contrast ratios
- **Loading states:** Skeleton screens and progress indicators

---

## Component Architecture

### Base Components

All components extend `LitElement` and follow consistent patterns:

```typescript
@customElement('component-name')
export class ComponentName extends LitElement {
  @state()
  private data: DataType[] = [];

  async connectedCallback() {
    super.connectedCallback();
    await this.fetchData();
  }

  async fetchData() {
    const response = await fetch('/api/endpoint');
    this.data = await response.json();
  }

  render() {
    return html`...`;
  }
}
```

### State Management

- **Reactive properties:** Using Lit's `@state()` and `@property()` decorators
- **Component communication:** Parent-child communication via properties
- **Global state:** No global state management (planned for future)

### Type Safety

Comprehensive TypeScript interfaces for all data structures:

```typescript
export interface Product {
  id: number;
  title: string;
  body_html: string;
  tags: string;
  category: string;
  normalized_title?: string;
  llm_confidence: number;
  gmc_category_label?: string;
  created_at: string;
  updated_at: string;
}
```

---

## Data Flow

### API Integration

All components follow a consistent pattern for API calls:

1. **Fetch on mount:** `connectedCallback()` triggers data loading
2. **Error handling:** Try-catch blocks with user-friendly error messages
3. **Loading states:** Visual indicators during API calls
4. **Data transformation:** Convert API responses to component state

### Real-time Updates

- **WebSocket support:** Real-time pipeline progress updates
- **Auto-refresh:** Configurable refresh intervals for dynamic data
- **Event-driven:** Component communication via custom events

---

## Performance Optimizations

### Build Process

```bash
# Build CSS
pnpm run build:css     # Tailwind compilation

# Build JavaScript
pnpm run build:js      # esbuild bundling

# Full build
pnpm run build         # Both CSS and JS
```

### Code Splitting

- **Component-based:** Each component loads independently
- **Tree shaking:** Unused code elimination via esbuild
- **Lazy loading:** Components load on-demand via routing

### Caching Strategy

- **Static assets:** Long-term caching with versioning
- **API responses:** Short-term caching for frequently accessed data
- **Browser caching:** Proper cache headers for optimal performance

---

## Development Features

### Hot Module Replacement (HMR)

- **Fast development:** Instant updates during development
- **State preservation:** Maintains component state during reloads
- **Error overlay:** Detailed error information in browser

### TypeScript Integration

- **Type checking:** Compile-time error detection
- **IntelliSense:** Enhanced IDE support
- **Refactoring:** Safe code modifications

### Build Monitoring

```bash
# Watch mode for continuous building
pnpm run watch

# Concurrent building of CSS and JS
concurrently "tailwindcss --watch" "esbuild --watch"
```

---

## Browser Compatibility

**Supported Browsers:**
- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

**Features Used:**
- ES2020+ syntax
- CSS Grid and Flexbox
- Web Components (Lit)
- Fetch API
- WebSocket API

---

## Accessibility Features

- **Keyboard navigation:** Full keyboard accessibility
- **Screen reader support:** Proper ARIA labels and semantic HTML
- **Color contrast:** WCAG AA compliance
- **Focus management:** Visible focus indicators
- **Alternative text:** Descriptive labels for interactive elements

---

## Future Enhancements

### Planned Features

1. **Advanced Search:** Full-text search across products
2. **Bulk Operations:** Multi-select actions for products
3. **Export Functionality:** CSV/Excel export capabilities
4. **User Management:** Role-based access control
5. **API Documentation:** Interactive API documentation
6. **Dark Mode:** Theme switching capability
7. **Mobile App:** Progressive Web App (PWA) features

### Technical Improvements

1. **State Management:** Global state with context or Redux
2. **Testing:** Unit and integration tests
3. **Performance Monitoring:** Real user monitoring (RUM)
4. **Internationalization:** Multi-language support
5. **Offline Support:** Service worker implementation

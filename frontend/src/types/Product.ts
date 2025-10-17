export interface ProductImage {
  id: number;
  src: string;
  position: number;
  width?: number;
  height?: number;
}

export interface ProductVariant {
  id: number;
  title: string;
  price: string;
  sku?: string;
  option1?: string;
  option2?: string;
  option3?: string;
}

export interface ProductOption {
  id: number;
  name: string;
  position: number;
  values: string[];
}

export interface Product {
  id: number;
  title: string;
  body_html?: string;
  category?: string;
  normalized_category?: string;
  normalized_title?: string;
  normalized_body_html?: string;
  llm_confidence?: number;
  gmc_category_label?: string;
  vendor_id?: number;
  vendor_name?: string;
  product_type_id?: number;
  product_type_name?: string;
  tags?: string[];
  images?: ProductImage[];
  variants?: ProductVariant[];
  options?: ProductOption[];
  created_at?: string;
  updated_at?: string;
  [key: string]: unknown;
}

export interface PaginatedProducts {
  products: Product[];
  total: number;
  page: number;
  limit: number;
  total_pages: number;
}

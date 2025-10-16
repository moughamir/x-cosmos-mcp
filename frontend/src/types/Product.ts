export interface Product {
  id: number;
  title: string;
  body_html: string;
  category: string;
  normalized_category: string;
  normalized_title: string;
  normalized_body_html: string;
  llm_confidence: number;
  gmc_category_label: string;
  [key: string]: unknown;
}

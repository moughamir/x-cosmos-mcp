export interface TaxonomyNode {
  name: string;
  full_path: string;
  children: { [key: string]: TaxonomyNode };
}

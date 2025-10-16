export interface TaxonomyNode {
  id: number;
  name: string;
  full_path: string;
  children: TaxonomyNode[];
}

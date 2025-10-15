export interface ChangeLogEntry {
  id: number;
  product_id: number;
  field: string;
  old: string;
  new: string;
  created_at: string;
  source: string;
  reviewed: number;
}

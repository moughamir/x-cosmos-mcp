export interface ChangeLogEntry {
  id: number;
  product_id: number;
  field: string;
  old: string;
  new: string;
  source: string;
  created_at: string; // ISO 8601 format string
  reviewed: boolean;
}

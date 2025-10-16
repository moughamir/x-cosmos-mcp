export interface ColumnSchema {
  name: string;
  type: string;
  // Add other relevant column properties if known, e.g., nullable, default, etc.
}

export interface TableSchema {
  name: string;
  columns: ColumnSchema[];
}

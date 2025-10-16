'use client';

import { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Skeleton } from '@/components/ui/skeleton';
import { toast } from "sonner";
import { TableSchema } from '@/types/TableSchema';

function SchemaSkeleton() {
  return (
    <div className="space-y-6">
      {[...Array(2)].map((_, i) => (
        <Card key={i}>
          <CardHeader>
            <Skeleton className="h-7 w-1/3" />
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {[...Array(4)].map((_, j) => (
                <div key={j} className="flex items-center space-x-4">
                  <Skeleton className="h-4 w-1/4" />
                  <Skeleton className="h-4 w-1/2" />
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

export default function DatabasePage() {
  const [schema, setSchema] = useState<TableSchema[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  useEffect(() => {
    const fetchSchema = async () => {
      setIsLoading(true);
      try {
        const response = await fetch('/api/db/schema');
        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || 'Failed to fetch database schema');
        }
        const data: { schema: TableSchema[] } = await response.json();
        setSchema(data.schema);
      } catch (e: any) {
        console.error('Error fetching schema:', e);
        toast.error(`Failed to load database schema: ${e.message}`);
      } finally {
        setIsLoading(false);
      }
    };

    fetchSchema();
  }, []);

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">Database Schema</h1>
      {isLoading ? (
        <SchemaSkeleton />
      ) : schema.length === 0 ? (
        <p>No database schema information available.</p>
      ) : (
        <div className="space-y-6">
          {schema.map((table) => (
            <Card key={table.table_name}>
              <CardHeader>
                <CardTitle>{table.table_name}</CardTitle>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Column</TableHead>
                      <TableHead>Type</TableHead>
                      <TableHead>Nullable</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {table.columns.map((col) => (
                      <TableRow key={col.name}>
                        <TableCell className="font-medium">{col.name}</TableCell>
                        <TableCell>{col.type}</TableCell>
                        <TableCell>{col.nullable ? 'Yes' : 'No'}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'; // Assuming Table components are available
import { TableSchema } from '@/types/TableSchema'; // Assuming types are migrated

const DbManagementPage = () => {
  const [dbSchema, setDbSchema] = useState<TableSchema[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [isMigrating, setIsMigrating] = useState<boolean>(false);

  const fetchDbSchema = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch('/api/schema', { cache: 'no-store' });
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data: TableSchema[] = await response.json();
      setDbSchema(data);
    } catch (e: any) {
      console.error('Error fetching DB schema:', e);
      setError(`Failed to load database schema: ${e.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchDbSchema();
  }, []);

  const runMigrations = async () => {
    if (!confirm('Are you sure you want to run database migrations? This can alter your database schema.')) {
      return;
    }
    setIsMigrating(true);
    setError(null);
    try {
      const response = await fetch('/api/db/migrate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || `HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      alert(`Migrations run successfully: ${result.message}`);
      fetchDbSchema(); // Refresh schema after migration
    } catch (e: any) {
      console.error('Error running migrations:', e);
      setError(`Failed to run migrations: ${e.message}`);
    } finally {
      setIsMigrating(false);
    }
  };

  return (
    <div className="container mx-auto p-4">
      <Card>
        <CardHeader>
          <CardTitle>Database Management</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-4 mb-6">
            <Button onClick={fetchDbSchema} variant="outline" disabled={isLoading}>
              Refresh Schema
            </Button>
            <Button onClick={runMigrations} variant="destructive" disabled={isMigrating}>
              {isMigrating ? 'Running Migrations...' : 'Run Migrations'}
            </Button>
          </div>

          <h2 className="text-xl font-bold mb-3">Current Schema</h2>
          {isLoading && <p>Loading schema...</p>}
          {error && <p className="text-red-500">Error: {error}</p>}
          {!isLoading && !error && dbSchema.length === 0 && (
            <p>No schema information available.</p>
          )}
          {!isLoading && !error && dbSchema.length > 0 && (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Table Name</TableHead>
                    <TableHead>Columns</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {dbSchema.map((table) => (
                    <TableRow key={table.name}>
                      <TableCell className="font-medium">{table.name}</TableCell>
                      <TableCell>
                        <ul className="list-disc list-inside">
                          {table.columns.map((col) => (
                            <li key={col.name}>{col.name} ({col.type})</li>
                          ))}
                        </ul>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default DbManagementPage;

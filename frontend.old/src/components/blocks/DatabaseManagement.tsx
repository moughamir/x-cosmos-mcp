'use client';

import React, { useState, useEffect } from 'react';
import { TableSchema } from '@/types/TableSchema';
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

interface DatabaseManagementProps {
  // Props if needed
}

const DatabaseManagement: React.FC<DatabaseManagementProps> = () => {
  const [dbSchema, setDbSchema] = useState<TableSchema[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isLoadingSchema, setIsLoadingSchema] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDbSchema = async () => {
    setIsLoadingSchema(true);
    setError(null);
    try {
      const response = await fetch('/api/schema');
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      setDbSchema(data || []);
    } catch (e: any) {
      console.error('Error fetching DB schema:', e);
      setError(`Failed to fetch schema: ${e.message}`);
    } finally {
      setIsLoadingSchema(false);
    }
  };

  useEffect(() => {
    fetchDbSchema();
  }, []);

  const runMigrations = async () => {
    if (!confirm('Are you sure you want to run database migrations? This can alter your database schema.')) {
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/db/migrate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      alert(`Migrations run successfully: ${result.message}`);
      await fetchDbSchema(); // Refresh schema after migration
    } catch (e: any) {
      console.error('Error running migrations:', e);
      setError(`Failed to run migrations: ${e.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Database Management</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {error && <p className="text-red-500">Error: {error}</p>}

        <div className="flex gap-2">
          <Button
            onClick={fetchDbSchema}
            disabled={isLoadingSchema}
            variant="outline"
          >
            {isLoadingSchema ? 'Refreshing...' : 'Refresh Schema'}
          </Button>
          <Button
            onClick={runMigrations}
            disabled={isLoading}
            variant="destructive"
          >
            {isLoading ? 'Running Migrations...' : 'Run Migrations'}
          </Button>
        </div>

        <div className="space-y-2">
          <h2 className="text-lg font-semibold">Current Schema</h2>
          {dbSchema.length === 0 ? (
            <p className="text-gray-500">No schema information available.</p>
          ) : (
            <div className="space-y-4">
              {dbSchema.map((table) => (
                <div key={table.name} className="border rounded-lg p-4 bg-gray-50">
                  <div className="flex items-center gap-2 mb-3">
                    <h3 className="font-semibold text-base">Table: {table.name}</h3>
                    <Badge variant="secondary">{table.columns.length} columns</Badge>
                  </div>
                  <div className="grid gap-1">
                    {table.columns.map((col) => (
                      <div key={col.name} className="flex justify-between items-center py-1 px-2 bg-white rounded border">
                        <span className="font-medium">{col.name}</span>
                        <Badge variant="outline">{col.type}</Badge>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
};

export default DatabaseManagement;

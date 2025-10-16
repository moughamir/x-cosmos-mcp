'use client';

import React, { useState, useEffect } from 'react';
import { ChangeLogEntry } from '@/types/ChangeLogEntry';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

interface ChangeLogProps {
  // Props if needed
}

const ChangeLog: React.FC<ChangeLogProps> = () => {
  const [changes, setChanges] = useState<ChangeLogEntry[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchChangeLog = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch('/api/changes');
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      setChanges(data.changes || []);
    } catch (e: any) {
      console.error('Error fetching change log:', e);
      setError(`Failed to fetch changes: ${e.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchChangeLog();
  }, []);

  const truncateText = (text: string, maxLength: number = 50) => {
    return text.length > maxLength ? `${text.substring(0, maxLength)}...` : text;
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Recent Changes</CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading && <p>Loading changes...</p>}
        {error && <p className="text-red-500">Error: {error}</p>}
        {!isLoading && !error && changes.length === 0 && (
          <p className="text-gray-500">No changes recorded yet.</p>
        )}
        {!isLoading && !error && changes.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b">
                  <th className="text-left p-2 font-semibold">ID</th>
                  <th className="text-left p-2 font-semibold">Product ID</th>
                  <th className="text-left p-2 font-semibold">Field</th>
                  <th className="text-left p-2 font-semibold">Old Value</th>
                  <th className="text-left p-2 font-semibold">New Value</th>
                  <th className="text-left p-2 font-semibold">Source</th>
                  <th className="text-left p-2 font-semibold">Date</th>
                  <th className="text-left p-2 font-semibold">Reviewed</th>
                </tr>
              </thead>
              <tbody>
                {changes.map((change) => (
                  <tr key={change.id} className="border-b hover:bg-gray-50">
                    <td className="p-2 font-mono text-sm">{change.id}</td>
                    <td className="p-2">
                      <a
                        href={`/admin/products/${change.product_id}`}
                        className="text-blue-500 hover:underline font-medium"
                      >
                        {change.product_id}
                      </a>
                    </td>
                    <td className="p-2">{change.field}</td>
                    <td className="p-2 max-w-xs">
                      <span title={change.old}>{truncateText(change.old)}</span>
                    </td>
                    <td className="p-2 max-w-xs">
                      <span title={change.new}>{truncateText(change.new)}</span>
                    </td>
                    <td className="p-2">{change.source}</td>
                    <td className="p-2 text-sm">
                      {new Date(change.created_at).toLocaleString()}
                    </td>
                    <td className="p-2">
                      <Badge variant={change.reviewed ? 'default' : 'destructive'}>
                        {change.reviewed ? 'Yes' : 'No'}
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default ChangeLog;

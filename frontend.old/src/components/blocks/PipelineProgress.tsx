'use client';

import React, { useState, useEffect } from 'react';
import { PipelineRun } from '@/types/PipelineRun';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { subscribeToPipelineUpdates } from '@/lib/websocket';

interface PipelineProgressProps {
  // Props if needed
}

const PipelineProgress: React.FC<PipelineProgressProps> = () => {
  const [pipelineRuns, setPipelineRuns] = useState<PipelineRun[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchPipelineRuns = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch('/api/pipeline/runs');
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      setPipelineRuns(data.runs || []);
    } catch (e: any) {
      console.error('Error fetching pipeline runs:', e);
      setError(`Failed to fetch pipeline runs: ${e.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    // Fetch initial data
    fetchPipelineRuns();

    // Subscribe to real-time WebSocket updates
    const unsubscribe = subscribeToPipelineUpdates((data) => {
      if (data.type === 'pipeline_runs_update' || data.type === 'pipeline_progress_update') {
        setPipelineRuns(data.pipeline_runs || pipelineRuns);
      }
    });

    // Cleanup subscription on unmount
    return () => {
      unsubscribe();
    };
  }, []);

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'completed':
        return 'bg-green-100 text-green-800';
      case 'running':
        return 'bg-blue-100 text-blue-800';
      case 'failed':
        return 'bg-red-100 text-red-800';
      case 'pending':
        return 'bg-yellow-100 text-yellow-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Pipeline Progress</CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading && <p>Loading pipeline runs...</p>}
        {error && <p className="text-red-500">Error: {error}</p>}
        {!isLoading && !error && pipelineRuns.length === 0 && (
          <p className="text-gray-500">No pipeline runs recorded yet.</p>
        )}
        {!isLoading && !error && pipelineRuns.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b">
                  <th className="text-left p-2 font-semibold">ID</th>
                  <th className="text-left p-2 font-semibold">Task Type</th>
                  <th className="text-left p-2 font-semibold">Status</th>
                  <th className="text-left p-2 font-semibold">Start Time</th>
                  <th className="text-left p-2 font-semibold">End Time</th>
                  <th className="text-left p-2 font-semibold">Total Products</th>
                  <th className="text-left p-2 font-semibold">Processed</th>
                  <th className="text-left p-2 font-semibold">Failed</th>
                </tr>
              </thead>
              <tbody>
                {pipelineRuns.map((run) => (
                  <tr key={run.id} className="border-b hover:bg-gray-50">
                    <td className="p-2 font-mono text-sm">{run.id}</td>
                    <td className="p-2 capitalize">{run.task_type.replace('_', ' ')}</td>
                    <td className="p-2">
                      <Badge className={getStatusColor(run.status)}>
                        {run.status}
                      </Badge>
                    </td>
                    <td className="p-2 text-sm">
                      {new Date(run.start_time).toLocaleString()}
                    </td>
                    <td className="p-2 text-sm">
                      {run.end_time ? new Date(run.end_time).toLocaleString() : 'N/A'}
                    </td>
                    <td className="p-2 text-center">{run.total_products}</td>
                    <td className="p-2 text-center">
                      <span className={run.processed_products > 0 ? 'text-green-600' : ''}>
                        {run.processed_products}
                      </span>
                    </td>
                    <td className="p-2 text-center">
                      <span className={run.failed_products > 0 ? 'text-red-600' : ''}>
                        {run.failed_products}
                      </span>
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

export default PipelineProgress;

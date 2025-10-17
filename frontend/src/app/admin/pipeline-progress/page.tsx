'use client';

import React, { useState, useEffect, useRef } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { toast } from "sonner";
import { PipelineRun } from '@/types/PipelineRun';

function ProgressTableSkeleton() {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>ID</TableHead>
          <TableHead>Task Type</TableHead>
          <TableHead>Status</TableHead>
          <TableHead>Start Time</TableHead>
          <TableHead>End Time</TableHead>
          <TableHead>Total</TableHead>
          <TableHead>Processed</TableHead>
          <TableHead>Failed</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {[...Array(3)].map((_, i) => (
          <TableRow key={i}>
            <TableCell><Skeleton className="h-4 w-8" /></TableCell>
            <TableCell><Skeleton className="h-4 w-32" /></TableCell>
            <TableCell><Skeleton className="h-6 w-20" /></TableCell>
            <TableCell><Skeleton className="h-4 w-40" /></TableCell>
            <TableCell><Skeleton className="h-4 w-40" /></TableCell>
            <TableCell><Skeleton className="h-4 w-12" /></TableCell>
            <TableCell><Skeleton className="h-4 w-12" /></TableCell>
            <TableCell><Skeleton className="h-4 w-12" /></TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

export default function PipelineProgressPage() {
  const [pipelineRuns, setPipelineRuns] = useState<PipelineRun[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const getWebSocketUrl = () => {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const wsUrl = apiUrl.replace(/^(http)/, 'ws');
      return `${wsUrl}/ws/pipeline-progress`;
    };

    const socketUrl = getWebSocketUrl();

    const connect = () => {
      socketRef.current = new WebSocket(socketUrl);

      socketRef.current.onopen = () => {
        console.log("WebSocket connected");
        setIsLoading(false);
        toast.success("Connected to pipeline updates.");
      };

      socketRef.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          if (data.type === 'initial_data' || data.type === 'pipeline_runs_update') {
            setPipelineRuns(data.pipeline_runs || []);
          } else if (data.type === 'pipeline_progress_update' && data.pipeline_runs) {
            setPipelineRuns(prevRuns => {
              const runsMap = new Map(prevRuns.map(run => [run.id, run]));
              data.pipeline_runs.forEach((updatedRun: PipelineRun) => {
                runsMap.set(updatedRun.id, { ...runsMap.get(updatedRun.id), ...updatedRun });
              });
              return Array.from(runsMap.values()).sort((a, b) => b.id - a.id);
            });
          }
        } catch (e) {
          console.error("Error processing WebSocket message:", e);
          toast.error("Error processing pipeline update.");
        }
      };

      socketRef.current.onclose = () => {
        console.log("WebSocket disconnected. Reconnecting in 5 seconds...");
        toast.info("Connection lost. Attempting to reconnect...");
        setTimeout(connect, 5000);
      };

      socketRef.current.onerror = (error) => {
        console.error("WebSocket error:", error);
        toast.error("WebSocket connection failed.");
        socketRef.current?.close();
      };
    };

    connect();

    return () => {
      if (socketRef.current) {
        socketRef.current.close();
      }
    };
  }, []);

  const formatDateTime = (isoString: string | null | undefined): string => {
    if (!isoString) return 'N/A';
    return new Date(isoString).toLocaleString();
  };

  const getStatusVariant = (status: string): "default" | "secondary" | "destructive" | "outline" => {
    switch (status.toLowerCase()) {
      case 'completed': return 'default';
      case 'running': return 'secondary';
      case 'failed': return 'destructive';
      case 'pending': return 'outline';
      default: return 'outline';
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Pipeline Progress</CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <ProgressTableSkeleton />
        ) : pipelineRuns.length === 0 ? (
          <p>No pipeline runs recorded yet. Waiting for updates...</p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>ID</TableHead>
                <TableHead>Task Type</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Start Time</TableHead>
                <TableHead>End Time</TableHead>
                <TableHead>Total</TableHead>
                <TableHead>Processed</TableHead>
                <TableHead>Failed</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {pipelineRuns.map((run) => (
                <TableRow key={run.id}>
                  <TableCell>{run.id}</TableCell>
                  <TableCell>{run.task_type}</TableCell>
                  <TableCell>
                    <Badge variant={getStatusVariant(run.status)} className={run.status === 'running' ? 'animate-pulse' : ''}>
                      {run.status}
                    </Badge>
                  </TableCell>
                  <TableCell>{formatDateTime(run.start_time)}</TableCell>
                  <TableCell>{formatDateTime(run.end_time)}</TableCell>
                  <TableCell>{run.total_products}</TableCell>
                  <TableCell>{run.processed_products}</TableCell>
                  <TableCell>{run.failed_products}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}

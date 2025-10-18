'use client';

import React, { useState, useEffect, useRef } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Progress } from '@/components/ui/progress';
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

interface CurrentProgress {
  id: number;
  processed: number;
  failed: number;
  total: number;
  percentage: number;
}

export default function PipelineProgressPage() {
  const [pipelineRuns, setPipelineRuns] = useState<PipelineRun[]>([]);
  const [currentProgress, setCurrentProgress] = useState<CurrentProgress | null>(null);
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
          if (typeof event.data === 'string') { // Ensure data is a string before parsing
            const data = JSON.parse(event.data);

            if (data.type === 'initial_data' || data.type === 'pipeline_progress_update') {
              if (data.pipeline_runs) {
                setPipelineRuns(data.pipeline_runs);
              }
              if (data.current_run) {
                setCurrentProgress(data.current_run);
              }
            }
          } else {
            console.warn("Received non-string WebSocket message:", event.data);
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
        {/* Live Progress Indicator */}
        {currentProgress && (
          <div className="mb-6 p-4 border rounded-lg bg-muted/50">
            <div className="flex justify-between items-center mb-2">
              <h3 className="text-sm font-medium">Current Pipeline Run #{currentProgress.id}</h3>
              <span className="text-sm text-muted-foreground">
                {currentProgress.processed + currentProgress.failed} / {currentProgress.total} products
              </span>
            </div>
            <Progress value={currentProgress.percentage} className="h-2 mb-2" />
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>✓ Processed: {currentProgress.processed}</span>
              <span>✗ Failed: {currentProgress.failed}</span>
              <span>{currentProgress.percentage.toFixed(1)}% Complete</span>
            </div>
          </div>
        )}

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

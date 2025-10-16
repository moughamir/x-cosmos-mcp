'use client';

import React, { useState, useEffect, useRef } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { PipelineRun } from '@/types/PipelineRun';

// Get WebSocket URL from environment variables
const socketUrl = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws/pipeline-progress'; // Fallback URL

const PipelineProgressPage = () => {
  const [pipelineRuns, setPipelineRuns] = useState<PipelineRun[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const socketRef = useRef<WebSocket | null>(null); // Use ref to hold socket instance

  const connectWebSocket = () => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      return; // Already connected
    }

    console.log(`Attempting to connect to WebSocket: ${socketUrl}`);
    socketRef.current = new WebSocket(socketUrl);

    socketRef.current.onopen = () => {
      console.log("WebSocket connected");
      setIsLoading(false); // Connection successful, stop loading indicator
      setError(null); // Clear any previous errors
    };

    socketRef.current.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log("WebSocket message received:", data);

        setPipelineRuns(prevRuns => {
          let updatedRuns = [...prevRuns];
          if (data.type === 'initial_data' || data.type === 'pipeline_runs_update') {
            // If it's initial data or a full update, replace or merge
            if (data.pipeline_runs) {
              // Simple merge: update existing, add new. More complex logic might be needed for large datasets.
              const newRunsMap = new Map(updatedRuns.map(run => [run.id, run]));
              data.pipeline_runs.forEach((run: PipelineRun) => newRunsMap.set(run.id, run));
              updatedRuns = Array.from(newRunsMap.values());
            }
          } else if (data.type === 'pipeline_progress_update') {
            // Update specific runs
            if (data.pipeline_runs) {
              data.pipeline_runs.forEach((updatedRun: PipelineRun) => {
                const existingIndex = updatedRuns.findIndex(run => run.id === updatedRun.id);
                if (existingIndex > -1) {
                  // Merge updates, prioritizing new data
                  updatedRuns[existingIndex] = { ...updatedRuns[existingIndex], ...updatedRun };
                } else {
                  // Add new run if it doesn't exist (though typically updates are for existing runs)
                  updatedRuns.push(updatedRun);
                }
              });
            }
          }
          return updatedRuns;
        });
      } catch (e) {
        console.error("Error processing WebSocket message:", e);
      }
    };

    socketRef.current.onclose = () => {
      console.log("WebSocket disconnected. Reconnecting in 5 seconds...");
      // Attempt to reconnect after a delay
      setTimeout(connectWebSocket, 5000);
    };

    socketRef.current.onerror = (error) => {
      console.error("WebSocket error:", error);
      setError("WebSocket connection error. See console for details.");
      // Close the socket to allow reconnection attempt
      socketRef.current?.close();
    };
  };

  useEffect(() => {
    connectWebSocket(); // Establish connection when component mounts

    // Cleanup function to close the WebSocket connection when the component unmounts
    return () => {
      if (socketRef.current) {
        console.log("Closing WebSocket connection.");
        socketRef.current.close();
        socketRef.current = null;
      }
    };
  }, []); // Empty dependency array ensures this runs only once on mount and cleanup on unmount

  // Helper function to format date
  const formatDateTime = (isoString: string | null | undefined): string => {
    if (!isoString) return 'N/A';
    try {
      return new Date(isoString).toLocaleString();
    } catch (e) {
      console.error("Error formatting date:", e);
      return isoString; // Return original string if formatting fails
    }
  };

  // Helper to determine status color
  const getStatusClass = (status: string): string => {
    switch (status.toLowerCase()) {
      case 'completed': return 'text-green-600 font-medium';
      case 'running': return 'text-blue-600 font-medium animate-pulse';
      case 'failed': return 'text-red-600 font-medium';
      case 'pending': return 'text-gray-600 font-medium';
      default: return 'text-gray-800';
    }
  };

  return (
    <div className="container mx-auto p-4">
      <Card>
        <CardHeader>
          <CardTitle>Pipeline Progress</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading && <p>Connecting to pipeline updates...</p>}
          {error && <p className="text-red-500">Error: {error}</p>}
          {!isLoading && !error && pipelineRuns.length === 0 && (
            <p>No pipeline runs recorded yet or waiting for updates.</p>
          )}
          {!isLoading && !error && pipelineRuns.length > 0 && (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>ID</TableHead>
                    <TableHead>Task Type</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Start Time</TableHead>
                    <TableHead>End Time</TableHead>
                    <TableHead>Total Products</TableHead>
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
                        <span className={getStatusClass(run.status)}>
                          {run.status}
                        </span>
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
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default PipelineProgressPage;

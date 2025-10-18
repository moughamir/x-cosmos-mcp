'use client';

import { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { fetchApi } from '@/lib/api';
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { toast } from "sonner";
import { PipelineRun } from '@/types/PipelineRun';
import { ChangeLogEntry } from '@/types/ChangeLogEntry';

interface RunDetailsResponse {
  run: PipelineRun;
  logs: ChangeLogEntry[];
}

import { DetailsSkeleton } from '@/components/ui/details-skeleton';
import { formatDateTime, getStatusVariant } from '@/lib/utils';

export default function PipelineRunDetailsPage() {
  const params = useParams();
  const runId = params.run_id as string;
  const [details, setDetails] = useState<RunDetailsResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (!runId) return;

    const fetchDetails = async () => {
      setIsLoading(true);
      try {
        const response = await fetchApi(`/api/pipeline/runs/${runId}`);
        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || 'Failed to fetch pipeline run details');
        }
        const data: RunDetailsResponse = await response.json();
        setDetails(data);
      } catch (e) {
        const errorMessage = e instanceof Error ? e.message : String(e);
        toast.error(`Failed to load details for run #${runId}: ${errorMessage}`);
      } finally {
        setIsLoading(false);
      }
    };

    fetchDetails();
  }, [runId]);

  if (isLoading) {
    return <DetailsSkeleton />;
  }

  if (!details || !details.run) {
    return <p>Pipeline run not found.</p>;
  }

  const { run, logs } = details;

  const successLogs = logs.filter(log => !log.field.endsWith('_error'));
  const errorLogs = logs.filter(log => log.field.endsWith('_error'));

  return (
    <div className="space-y-6">
      <Link href="/admin/pipeline-progress" className="text-sm font-medium text-muted-foreground hover:text-primary">
        &larr; Back to All Runs
      </Link>

      <Card>
        <CardHeader>
          <CardTitle>Pipeline Run #{run.id}</CardTitle>
          <CardDescription>
            Task: {run.task_type} | Status: <Badge variant={getStatusVariant(run.status)}>{run.status}</Badge>
          </CardDescription>
        </CardHeader>
        <CardContent className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
          <div className="flex flex-col space-y-1">
            <span className="text-muted-foreground">Start Time</span>
            <span>{formatDateTime(run.start_time)}</span>
          </div>
          <div className="flex flex-col space-y-1">
            <span className="text-muted-foreground">End Time</span>
            <span>{formatDateTime(run.end_time)}</span>
          </div>
          <div className="flex flex-col space-y-1">
            <span className="text-muted-foreground">Products</span>
            <span>{run.processed_products} / {run.total_products} processed ({run.failed_products} failed)</span>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Logs</CardTitle>
          <CardDescription>Detailed logs for each product in the run.</CardDescription>
        </CardHeader>
        <CardContent>
          {logs.length === 0 ? (
            <p>No logs found for this run.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Product ID</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Details</TableHead>
                  <TableHead>Timestamp</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {errorLogs.map(log => (
                  <TableRow key={log.id} className="bg-destructive/10">
                    <TableCell>
                      <Link href={`/admin/products/${log.product_id}`} className="font-medium text-primary hover:underline">
                        {log.product_id}
                      </Link>
                    </TableCell>
                    <TableCell>
                      <Badge variant="destructive">Failed</Badge>
                    </TableCell>
                    <TableCell className="font-mono text-xs">{log.new}</TableCell>
                    <TableCell>{formatDateTime(log.created_at)}</TableCell>
                  </TableRow>
                ))}
                {successLogs.map(log => (
                  <TableRow key={log.id}>
                    <TableCell>
                      <Link href={`/admin/products/${log.product_id}`} className="font-medium text-primary hover:underline">
                        {log.product_id}
                      </Link>
                    </TableCell>
                    <TableCell>
                      <Badge variant="default">Success</Badge>
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">{log.field}</TableCell>
                    <TableCell>{formatDateTime(log.created_at)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

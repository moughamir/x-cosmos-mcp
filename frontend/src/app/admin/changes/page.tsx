import Link from 'next/link';
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Badge } from "@/components/ui/badge";
import { ChangeLogEntry } from '@/types/ChangeLogEntry';

async function getChanges(): Promise<{ changes: ChangeLogEntry[] }> {
  const res = await fetch('/api/changes', {
    cache: 'no-store',
  });

  if (!res.ok) {
    throw new Error('Failed to fetch changes');
  }

  const data = await res.json();
  return data;
}

const formatDateTime = (isoString: string): string => {
  if (!isoString) return 'N/A';
  return new Date(isoString).toLocaleString();
};

function TruncatedContent({ content }: { content: string | null }) {
  if (!content) return null;
  const isTruncated = content.length > 50;

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger>
          <span className="cursor-default">
            {isTruncated ? `${content.substring(0, 50)}...` : content}
          </span>
        </TooltipTrigger>
        {isTruncated && (
          <TooltipContent>
            <pre className="max-w-md p-2">{content}</pre>
          </TooltipContent>
        )}
      </Tooltip>
    </TooltipProvider>
  );
}

export default async function ChangesPage() {
  const { changes } = await getChanges();

  return (
    <Card>
      <CardHeader>
        <CardTitle>Recent Changes</CardTitle>
      </CardHeader>
      <CardContent>
        {changes.length === 0 ? (
          <p>No changes recorded yet.</p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>ID</TableHead>
                <TableHead>Product ID</TableHead>
                <TableHead>Field</TableHead>
                <TableHead>Old Value</TableHead>
                <TableHead>New Value</TableHead>
                <TableHead>Source</TableHead>
                <TableHead>Date</TableHead>
                <TableHead>Reviewed</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {changes.map((change) => (
                <TableRow key={change.id}>
                  <TableCell>{change.id}</TableCell>
                  <TableCell>
                    <Link href={`/admin/products/${change.product_id}`} className="font-medium text-primary hover:underline">
                      {change.product_id}
                    </Link>
                  </TableCell>
                  <TableCell>{change.field}</TableCell>
                  <TableCell>
                    <TruncatedContent content={change.old} />
                  </TableCell>
                  <TableCell>
                    <TruncatedContent content={change.new} />
                  </TableCell>
                  <TableCell>{change.source}</TableCell>
                  <TableCell>{formatDateTime(change.created_at)}</TableCell>
                  <TableCell>
                    <Badge variant={change.reviewed ? "default" : "destructive"}>
                      {change.reviewed ? 'Yes' : 'No'}
                    </Badge>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}

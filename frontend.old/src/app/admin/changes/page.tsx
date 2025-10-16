import Link from 'next/link';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { ChangeLogEntry } from '@/types/ChangeLogEntry'; // Assuming types are migrated

async function getChanges(): Promise<ChangeLogEntry[]> {
  // Fetch from the backend API
  const res = await fetch('http://localhost:8000/api/changes', {
    cache: 'no-store', // To ensure fresh data on each request
  });

  if (!res.ok) {
    throw new Error('Failed to fetch changes');
  }

  const data = await res.json();
  return data;
}

// Helper function to format date
const formatDateTime = (isoString: string): string => {
  if (!isoString) return 'N/A';
  try {
    return new Date(isoString).toLocaleString();
  } catch (e) {
    console.error("Error formatting date:", e);
    return isoString; // Return original string if formatting fails
  }
};

export default async function ChangesPage() {
  const changes = await getChanges();

  return (
    <div className="container mx-auto p-4">
      <Card>
        <CardHeader>
          <CardTitle>Recent Changes</CardTitle>
        </CardHeader>
        <CardContent>
          {changes.length === 0 ? (
            <p>No changes recorded yet.</p>
          ) : (
            <div className="overflow-x-auto"> {/* For responsiveness on smaller screens */}
              <table className="min-w-full bg-white">
                <thead>
                  <tr>
                    <th className="py-2 px-4 border-b text-left">ID</th>
                    <th className="py-2 px-4 border-b text-left">Product ID</th>
                    <th className="py-2 px-4 border-b text-left">Field</th>
                    <th className="py-2 px-4 border-b text-left">Old Value</th>
                    <th className="py-2 px-4 border-b text-left">New Value</th>
                    <th className="py-2 px-4 border-b text-left">Source</th>
                    <th className="py-2 px-4 border-b text-left">Date</th>
                    <th className="py-2 px-4 border-b text-left">Reviewed</th>
                  </tr>
                </thead>
                <tbody>
                  {changes.map((change) => (
                    <tr key={change.id} className="hover:bg-gray-50">
                      <td className="py-2 px-4 border-b">{change.id}</td>
                      <td className="py-2 px-4 border-b">
                        <Link
                          href={`/products/${change.product_id}`}
                          className="text-blue-600 hover:underline font-medium"
                        >
                          {change.product_id}
                        </Link>
                      </td>
                      <td className="py-2 px-4 border-b">{change.field}</td>
                      <td className="py-2 px-4 border-b">
                        {change.old && change.old.length > 50
                          ? `${change.old.substring(0, 50)}...`
                          : change.old}
                      </td>
                      <td className="py-2 px-4 border-b">
                        {change.new && change.new.length > 50
                          ? `${change.new.substring(0, 50)}...`
                          : change.new}
                      </td>
                      <td className="py-2 px-4 border-b">{change.source}</td>
                      <td className="py-2 px-4 border-b">{formatDateTime(change.created_at)}</td>
                      <td className="py-2 px-4 border-b">
                        <span
                          className={`font-medium ${change.reviewed ? 'text-green-600' : 'text-red-600'}`}
                        >
                          {change.reviewed ? 'Yes' : 'No'}
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
    </div>
  );
}

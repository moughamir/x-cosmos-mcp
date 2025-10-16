import Link from 'next/link';
import { Product } from '@/types/Product';
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
import { Button } from "@/components/ui/button";

async function getProducts(): Promise<{ products: Product[] }> {
  // Fetching from the proxied backend API
  const res = await fetch('/api/products', {
    cache: 'no-store',
  });

  if (!res.ok) {
    throw new Error('Failed to fetch products');
  }

  const data = await res.json();
  return data;
}

export default async function ProductsPage() {
  const { products } = await getProducts();

  return (
    <Card>
      <CardHeader>
        <CardTitle>Products</CardTitle>
      </CardHeader>
      <CardContent>
        {products.length === 0 ? (
          <p>No products found.</p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>ID</TableHead>
                <TableHead>Title</TableHead>
                <TableHead>Confidence</TableHead>
                <TableHead>Category</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {products.map((product) => (
                <TableRow key={product.id}>
                  <TableCell>{product.id}</TableCell>
                  <TableCell>{product.title}</TableCell>
                  <TableCell>
                    {product.llm_confidence ? product.llm_confidence.toFixed(2) : 'N/A'}
                  </TableCell>
                  <TableCell>{product.gmc_category_label || 'N/A'}</TableCell>
                  <TableCell>
                    <Button asChild variant="outline" size="sm">
                      <Link href={`/admin/products/${product.id}`}>
                        View
                      </Link>
                    </Button>
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

import { fetchApi } from '@/lib/api';
import { Product } from '@/types/Product';
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { ProductTable } from './ProductTable';

async function getProducts(): Promise<{ products: Product[] }> {
  const res = await fetchApi('/api/products', {
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
        <ProductTable products={products} />
      </CardContent>
    </Card>
  );
}

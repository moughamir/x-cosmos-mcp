import Link from 'next/link';
import { Product } from '@/types/Product'; // Assuming types are migrated

// Get backend API URL from environment variables
const backendApiUrl = process.env.NEXT_PUBLIC_BACKEND_API_URL || 'http://localhost:8000';

async function getProducts(): Promise<{ products: Product[] }> {
  // Fetching from the backend API
  const res = await fetch(`${backendApiUrl}/api/products`, {
    cache: 'no-store', // To ensure fresh data on each request
  });

  if (!res.ok) {
    // This will activate the closest `error.js` Error Boundary
    throw new Error('Failed to fetch products');
  }

  const data = await res.json();
  return data;
}

export default async function ProductsPage() {
  const { products } = await getProducts();

  return (
    <div className="container mx-auto p-4">
      <h1 className="text-2xl font-bold mb-4">Products</h1>
      {products.length === 0 ? (
        <p>No products found.</p>
      ) : (
        <table className="min-w-full bg-white">
          <thead>
            <tr>
              <th className="py-2 px-4 border-b text-left">ID</th>
              <th className="py-2 px-4 border-b text-left">Title</th>
              <th className="py-2 px-4 border-b text-left">Confidence</th>
              <th className="py-2 px-4 border-b text-left">Category</th>
              <th className="py-2 px-4 border-b text-left">Actions</th>
            </tr>
          </thead>
          <tbody>
            {products.map((product) => (
              <tr key={product.id}>
                <td className="py-2 px-4 border-b">{product.id}</td>
                <td className="py-2 px-4 border-b">{product.title}</td>
                <td className="py-2 px-4 border-b">
                  {product.llm_confidence.toFixed(2)}
                </td>
                <td className="py-2 px-4 border-b">{product.gmc_category_label}</td>
                <td className="py-2 px-4 border-b">
                  <Link
                    href={`/products/${product.id}`}
                    className="px-3 py-1 bg-blue-500 hover:bg-blue-700 text-white text-sm rounded transition-colors inline-block"
                  >
                    View
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

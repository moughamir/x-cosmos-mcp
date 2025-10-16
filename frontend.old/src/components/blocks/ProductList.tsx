'use client';

import React, { useState, useEffect } from 'react';
import { Product } from '@/types/Product';
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';

interface ProductListProps {
  // You might pass filters or other props later
}

const ProductList: React.FC<ProductListProps> = () => {
  const [products, setProducts] = useState<Product[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchProducts = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch('/api/products');
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      setProducts(data.products || []);
    } catch (e: any) {
      console.error('Error fetching products:', e);
      setError(`Failed to load products: ${e.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchProducts();
  }, []);

  const navigateToProductDetail = (productId: number) => {
    // In Next.js, we can use router.push or Link component
    window.location.href = `/admin/products/${productId}`;
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Products</CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading && <p>Loading products...</p>}
        {error && <p className="text-red-500">Error: {error}</p>}
        {!isLoading && !error && products.length === 0 && (
          <p>No products found.</p>
        )}
        {!isLoading && !error && products.length > 0 && (
          <div className="overflow-x-auto">
            <div className="grid grid-cols-5 gap-4 p-4 font-semibold border-b">
              <div>ID</div>
              <div>Title</div>
              <div>Confidence</div>
              <div>Category</div>
              <div>Actions</div>
            </div>
            {products.map((product) => (
              <div key={product.id} className="grid grid-cols-5 gap-4 p-4 border-b hover:bg-gray-50">
                <div className="font-mono text-sm">{product.id}</div>
                <div className="truncate" title={product.title}>{product.title}</div>
                <div>{product.llm_confidence?.toFixed(2) || 'N/A'}</div>
                <div className="truncate" title={product.gmc_category_label || ''}>
                  {product.gmc_category_label || 'No category'}
                </div>
                <div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => navigateToProductDetail(product.id)}
                  >
                    View
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default ProductList;

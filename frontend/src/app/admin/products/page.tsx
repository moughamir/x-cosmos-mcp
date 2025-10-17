'use client';

import { useState, useEffect, useCallback } from 'react';
import { fetchApi } from '@/lib/api';
import { PaginatedProducts } from '@/types/Product';
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { ProductTable } from './ProductTable';
import { Skeleton } from "@/components/ui/skeleton";

export default function ProductsPage() {
  const [data, setData] = useState<PaginatedProducts | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filter states
  const [page, setPage] = useState(1);
  const [limit, setLimit] = useState(50);
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('');
  const [minConfidence, setMinConfidence] = useState<number | null>(null);
  const [maxConfidence, setMaxConfidence] = useState<number | null>(null);

  const loadProducts = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams({
        page: page.toString(),
        limit: limit.toString(),
      });

      if (search) params.append('search', search);
      if (category) params.append('category', category);
      if (minConfidence !== null) params.append('min_confidence', minConfidence.toString());
      if (maxConfidence !== null) params.append('max_confidence', maxConfidence.toString());

      const res = await fetchApi(`/api/products?${params.toString()}`);

      if (!res.ok) {
        throw new Error('Failed to fetch products');
      }

      const result = await res.json();
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  }, [page, limit, search, category, minConfidence, maxConfidence]);

  useEffect(() => {
    loadProducts();
  }, [loadProducts]);

  const handlePageChange = (newPage: number) => {
    setPage(newPage);
  };

  const handleLimitChange = (newLimit: number) => {
    setLimit(newLimit);
    setPage(1); // Reset to first page when changing limit
  };

  const handleSearchChange = (newSearch: string) => {
    setSearch(newSearch);
    setPage(1); // Reset to first page when searching
  };

  const handleCategoryChange = (newCategory: string) => {
    setCategory(newCategory);
    setPage(1); // Reset to first page when filtering
  };

  const handleConfidenceChange = (min: number | null, max: number | null) => {
    setMinConfidence(min);
    setMaxConfidence(max);
    setPage(1); // Reset to first page when filtering
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Products</CardTitle>
      </CardHeader>
      <CardContent>
        {error && (
          <div className="text-red-500 text-sm p-4 bg-red-50 rounded mb-4">
            {error}
          </div>
        )}

        {loading && !data ? (
          <div className="space-y-4">
            <Skeleton className="h-12 w-full" />
            <Skeleton className="h-64 w-full" />
          </div>
        ) : data ? (
          <ProductTable
            products={data.products}
            total={data.total}
            page={data.page}
            limit={data.limit}
            totalPages={data.total_pages}
            onPageChange={handlePageChange}
            onLimitChange={handleLimitChange}
            onSearchChange={handleSearchChange}
            onCategoryChange={handleCategoryChange}
            onConfidenceChange={handleConfidenceChange}
          />
        ) : null}
      </CardContent>
    </Card>
  );
}

'use client';

import { useState, useEffect, ChangeEvent, FormEvent } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { fetchApi } from '@/lib/api';
import { Product } from '@/types/Product';
import { ChangeLogEntry } from '@/types/ChangeLogEntry';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Skeleton } from '@/components/ui/skeleton';
import { toast } from "sonner";

const formatDateTime = (isoString: string): string => {
  if (!isoString) return 'N/A';
  try {
    return new Date(isoString).toLocaleString();
  } catch (e) {
    console.error("Error formatting date:", e);
    return isoString;
  }
};

function ProductDetailSkeleton() {
  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <Skeleton className="h-8 w-3/4" />
        </CardHeader>
        <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="space-y-2">
            <Skeleton className="h-4 w-1/4" />
            <Skeleton className="h-10 w-full" />
          </div>
          <div className="space-y-2">
            <Skeleton className="h-4 w-1/4" />
            <Skeleton className="h-10 w-full" />
          </div>
          <div className="md:col-span-2 space-y-2">
            <Skeleton className="h-4 w-1/4" />
            <Skeleton className="h-24 w-full" />
          </div>
        </CardContent>
        <CardFooter>
          <Skeleton className="h-10 w-24" />
        </CardFooter>
      </Card>
    </div>
  );
}


export default function ProductDetailPage() {
  const params = useParams();
  const productId = params.id as string | undefined;

  const [product, setProduct] = useState<Product | null>(null);
  const [changes, setChanges] = useState<ChangeLogEntry[]>([]);
  const [editedProduct, setEditedProduct] = useState<Partial<Product>>({});
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState<boolean>(false);

  useEffect(() => {
    const fetchProductDetails = async () => {
      if (!productId) {
        setError('Product ID is missing.');
        setIsLoading(false);
        return;
      }
      setIsLoading(true);
      setError(null);
      try {
        const response = await fetchApi(`/api/products/${productId}`);
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        setProduct(data.product);
        setChanges(data.changes || []);
        setEditedProduct(data.product); // Initialize form with product data
      } catch (e) {
        console.error('Error fetching product details:', e);
        const errorMessage = e instanceof Error ? e.message : String(e);
        setError(`Failed to load product details: ${errorMessage}`);
        toast.error(`Failed to load product details: ${errorMessage}`);
      } finally {
        setIsLoading(false);
      }
    };

    fetchProductDetails();
  }, [productId]);

  const handleInputChange = (e: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setEditedProduct(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!productId) return;

    setIsSaving(true);
    setError(null);
    try {
      const response = await fetchApi(`/api/products/${productId}/update`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(editedProduct),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || `HTTP error! status: ${response.status}`);
      }

      const updatedData = await response.json();
      setProduct(updatedData.product);
      setChanges(updatedData.changes || []);
      setEditedProduct(updatedData.product);
      toast.success('Product updated successfully!');

    } catch (e) {
      console.error('Error saving changes:', e);
      const errorMessage = e instanceof Error ? e.message : String(e);
      setError(`Failed to save changes: ${errorMessage}`);
      toast.error(`Failed to save changes: ${errorMessage}`);
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading) {
    return <ProductDetailSkeleton />;
  }

  if (error && !product) {
    return <div className="text-red-500">Error: {error}</div>;
  }

  if (!product) {
    return <div>Product not found.</div>;
  }

  return (
    <div className="space-y-6">
      <Link href="/admin/products" className="text-sm font-medium text-muted-foreground hover:text-primary">
        &larr; Back to Products
      </Link>

      <form onSubmit={handleSubmit}>
        <Card>
          <CardHeader>
            <CardTitle>Edit Product: {product.title}</CardTitle>
          </CardHeader>
          <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-2">
              <Label htmlFor="title">Title</Label>
              <Input id="title" name="title" value={editedProduct.title ?? ''} onChange={handleInputChange} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="category">Category</Label>
              <Input id="category" name="category" value={editedProduct.category ?? ''} onChange={handleInputChange} />
            </div>
            <div className="md:col-span-2 space-y-2">
              <Label htmlFor="body_html">Body HTML</Label>
              <Textarea id="body_html" name="body_html" value={editedProduct.body_html ?? ''} onChange={handleInputChange} className="min-h-[150px]" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="gmc_category_label">GMC Category Label</Label>
              <Input id="gmc_category_label" name="gmc_category_label" value={editedProduct.gmc_category_label ?? ''} onChange={handleInputChange} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="llm_confidence">LLM Confidence</Label>
              <Input id="llm_confidence" name="llm_confidence" type="number" value={editedProduct.llm_confidence ?? ''} onChange={handleInputChange} />
            </div>
          </CardContent>
          <CardFooter className="flex justify-between">
            <Button type="submit" disabled={isSaving}>
              {isSaving ? 'Saving...' : 'Save Changes'}
            </Button>
            {error && <p className="text-red-500 text-sm">{error}</p>}
          </CardFooter>
        </Card>
      </form>

      <div className="space-y-4">
        <h2 className="text-2xl font-bold">Change Log</h2>
        {changes.length === 0 ? (
          <p>No changes recorded for this product.</p>
        ) : (
          <div className="space-y-4">
            {changes.map((change) => (
              <Card key={change.id}>
                <CardContent className="p-4 grid grid-cols-2 gap-x-4 gap-y-2">
                  <div><span className="font-semibold">Field:</span> {change.field}</div>
                  <div><span className="font-semibold">Source:</span> {change.source}</div>
                  <div className="col-span-2"><span className="font-semibold">Old Value:</span> <pre className="text-xs bg-muted p-2 rounded-md">{change.old}</pre></div>
                  <div className="col-span-2"><span className="font-semibold">New Value:</span> <pre className="text-xs bg-muted p-2 rounded-md">{change.new}</pre></div>
                  <div><span className="font-semibold">Date:</span> {formatDateTime(change.created_at)}</div>
                  <div><span className="font-semibold">Reviewed:</span> {change.reviewed ? 'Yes' : 'No'}</div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

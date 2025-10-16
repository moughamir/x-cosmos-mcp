'use client'; // This component will be a Client Component to handle form state and updates

import { useState, useEffect, ChangeEvent } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation'; // For dynamic route segments
import { Product } from '@/types/Product';
import { ChangeLogEntry } from '@/types/ChangeLogEntry';
import { Button } from '@/components/ui/button'; // Assuming Button is added via shadcn/ui
import { Input } from '@/components/ui/input'; // Assuming Input is added via shadcn/ui
import { Textarea } from '@/components/ui/textarea'; // Assuming Textarea is added via shadcn/ui
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from '@/components/ui/card'; // For layout

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

export default function ProductDetailPage() {
  const params = useParams();
  const productId = params.id as string | undefined; // Get ID from URL

  const [product, setProduct] = useState<Product | undefined>(undefined);
  const [changes, setChanges] = useState<ChangeLogEntry[]>([]);
  const [editedProduct, setEditedProduct] = useState<Partial<Product>>({});
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState<boolean>(false);

  const fetchProductDetails = async () => {
    if (!productId) {
      setError('Product ID is missing.');
      setIsLoading(false);
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      // Fetch product details and changes log
      const response = await fetch(`/api/products/${productId}`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      setProduct(data.product);
      setChanges(data.changes || []);
      // Initialize editedProduct with current product data
      setEditedProduct({ ...data.product });
    } catch (e: any) {
      console.error('Error fetching product details:', e);
      setError(`Failed to load product details: ${e.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchProductDetails();
  }, [productId]); // Re-fetch if productId changes

  const handleInputChange = (e: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setEditedProduct(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const saveChanges = async () => {
    if (!productId || Object.keys(editedProduct).length === 0) {
      // No changes to save or no product loaded
      return;
    }
    setIsSaving(true);
    setError(null);
    try {
      const response = await fetch(`/api/products/${productId}/update`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(editedProduct),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || `HTTP error! status: ${response.status}`);
      }

      alert('Product updated successfully!');
      // Clear editedProduct state after successful save to reflect changes
      setEditedProduct({});
      // Re-fetch details to show updated data and potentially new changes log
      await fetchProductDetails();
    } catch (e: any) {
      console.error('Error saving changes:', e);
      setError(`Failed to save changes: ${e.message}`);
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading) {
    return <div className="container mx-auto p-4">Loading product details...</div>;
  }

  if (error) {
    return <div className="container mx-auto p-4 text-red-500">Error: {error}</div>;
  }

  if (!product) {
    return <div className="container mx-auto p-4">Product not found.</div>;
  }

  return (
    <div className="container mx-auto p-4">
      <Link href="/products" className="text-blue-600 hover:underline mb-4 inline-block">
        &larr; Back to Products
      </Link>
      <Card>
        <CardHeader>
          <CardTitle>Product Detail: {product.title}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Form Fields */}
            <div className="form-group">
              <label htmlFor="title">Title</label>
              <Input
                id="title"
                name="title"
                value={editedProduct.title ?? product.title ?? ''}
                onChange={handleInputChange}
              />
            </div>
            <div className="form-group">
              <label htmlFor="category">Category</label>
              <Input
                id="category"
                name="category"
                value={editedProduct.category ?? product.category ?? ''}
                onChange={handleInputChange}
              />
            </div>
            <div className="form-group md:col-span-2">
              <label htmlFor="body_html">Body HTML</label>
              <Textarea
                id="body_html"
                name="body_html"
                value={editedProduct.body_html ?? product.body_html ?? ''}
                onChange={handleInputChange}
                className="min-h-[150px]"
              />
            </div>
            <div className="form-group">
              <label htmlFor="normalized_category">Normalized Category</label>
              <Input
                id="normalized_category"
                name="normalized_category"
                value={editedProduct.normalized_category ?? product.normalized_category ?? ''}
                onChange={handleInputChange}
              />
            </div>
            <div className="form-group">
              <label htmlFor="normalized_title">Normalized Title</label>
              <Input
                id="normalized_title"
                name="normalized_title"
                value={editedProduct.normalized_title ?? product.normalized_title ?? ''}
                onChange={handleInputChange}
              />
            </div>
            <div className="form-group md:col-span-2">
              <label htmlFor="normalized_body_html">Normalized Body HTML</label>
              <Textarea
                id="normalized_body_html"
                name="normalized_body_html"
                value={editedProduct.normalized_body_html ?? product.normalized_body_html ?? ''}
                onChange={handleInputChange}
                className="min-h-[150px]"
              />
            </div>
            <div className="form-group">
              <label htmlFor="gmc_category_label">GMC Category Label</label>
              <Input
                id="gmc_category_label"
                name="gmc_category_label"
                value={editedProduct.gmc_category_label ?? product.gmc_category_label ?? ''}
                onChange={handleInputChange}
              />
            </div>
            <div className="form-group">
              <label htmlFor="llm_confidence">LLM Confidence</label>
              <Input
                id="llm_confidence"
                name="llm_confidence"
                type="number" // Use number input for confidence
                value={editedProduct.llm_confidence ?? product.llm_confidence ?? ''}
                onChange={handleInputChange}
              />
            </div>
          </div>
        </CardContent>
        <CardFooter>
          <Button onClick={saveChanges} disabled={isSaving || Object.keys(editedProduct).length === 0}>
            {isSaving ? 'Saving...' : 'Save Changes'}
          </Button>
          {error && <p className="text-red-500 ml-4">Error: {error}</p>}
        </CardFooter>
      </Card>

      {/* Change Log Section */}
      <div className="changes-log mt-8">
        <h2 className="text-xl font-bold mb-2">Change Log</h2>
        {changes.length === 0 ? (
          <p>No changes recorded for this product.</p>
        ) : (
          <div className="space-y-4">
            {changes.map((change) => (
              <Card key={change.id} className="change-entry p-4">
                <CardContent className="p-0">
                  <p><span className="font-semibold">Field:</span> {change.field}</p>
                  <p><span className="font-semibold">Old Value:</span> {change.old}</p>
                  <p><span className="font-semibold">New Value:</span> {change.new}</p>
                  <p><span className="font-semibold">Source:</span> {change.source}</p>
                  <p><span className="font-semibold">Date:</span> {formatDateTime(change.created_at)}</p>
                  <p><span className="font-semibold">Reviewed:</span> {change.reviewed ? 'Yes' : 'No'}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

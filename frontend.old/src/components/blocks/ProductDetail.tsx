'use client';

import React, { useState, useEffect } from 'react';
import { Product } from '@/types/Product';
import { ChangeLogEntry } from '@/types/ChangeLogEntry';
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';

interface ProductDetailProps {
  productId?: number;
}

const ProductDetail: React.FC<ProductDetailProps> = ({ productId }) => {
  const [product, setProduct] = useState<Product | null>(null);
  const [changes, setChanges] = useState<ChangeLogEntry[]>([]);
  const [editedProduct, setEditedProduct] = useState<Partial<Product>>({});
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchProductDetails = async (id: number) => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch(`/api/products/${id}`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      setProduct(data.product);
      setChanges(data.changes || []);
      setEditedProduct({ ...data.product });
    } catch (e: any) {
      console.error('Error fetching product details:', e);
      setError(`Failed to load product: ${e.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    // Extract product_id from the URL if not provided as prop
    if (!productId) {
      const path = window.location.pathname;
      const parts = path.split('/');
      const id = parseInt(parts[parts.length - 1], 10);
      if (!isNaN(id)) {
        productId = id;
      }
    }

    if (productId) {
      fetchProductDetails(productId);
    }
  }, [productId]);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setEditedProduct(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const saveChanges = async () => {
    if (!productId || !product) return;

    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch(`/api/products/${productId}/update`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(editedProduct)
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      alert('Product updated successfully!');
      await fetchProductDetails(productId); // Re-fetch to update UI and changes log
    } catch (e: any) {
      console.error('Error saving changes:', e);
      setError(`Failed to save changes: ${e.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  if (isLoading) {
    return (
      <Card>
        <CardContent className="p-6">
          <p>Loading product details...</p>
        </CardContent>
      </Card>
    );
  }

  if (error || !product) {
    return (
      <Card>
        <CardContent className="p-6">
          <p className="text-red-500">Error: {error || 'Product not found'}</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Product Detail: {product.title}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="title">Title</Label>
              <Input
                id="title"
                name="title"
                value={editedProduct.title || ''}
                onChange={handleInputChange}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="category">Category</Label>
              <Input
                id="category"
                name="category"
                value={editedProduct.category || ''}
                onChange={handleInputChange}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="normalized_category">Normalized Category</Label>
              <Input
                id="normalized_category"
                name="normalized_category"
                value={editedProduct.normalized_category || ''}
                onChange={handleInputChange}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="normalized_title">Normalized Title</Label>
              <Input
                id="normalized_title"
                name="normalized_title"
                value={editedProduct.normalized_title || ''}
                onChange={handleInputChange}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="gmc_category_label">GMC Category Label</Label>
              <Input
                id="gmc_category_label"
                name="gmc_category_label"
                value={editedProduct.gmc_category_label || ''}
                onChange={handleInputChange}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="llm_confidence">LLM Confidence</Label>
              <Input
                id="llm_confidence"
                name="llm_confidence"
                type="number"
                step="0.01"
                value={editedProduct.llm_confidence || ''}
                onChange={handleInputChange}
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="body_html">Body HTML</Label>
            <Textarea
              id="body_html"
              name="body_html"
              value={editedProduct.body_html || ''}
              onChange={handleInputChange}
              rows={4}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="normalized_body_html">Normalized Body HTML</Label>
            <Textarea
              id="normalized_body_html"
              name="normalized_body_html"
              value={editedProduct.normalized_body_html || ''}
              onChange={handleInputChange}
              rows={4}
            />
          </div>

          <Button onClick={saveChanges} disabled={isLoading}>
            Save Changes
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Change Log</CardTitle>
        </CardHeader>
        <CardContent>
          {changes.length === 0 ? (
            <p>No changes recorded for this product.</p>
          ) : (
            <div className="space-y-4">
              {changes.map((change, index) => (
                <div key={index} className="border rounded-lg p-4 bg-gray-50">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-sm">
                    <div><strong>Field:</strong> {change.field}</div>
                    <div><strong>Source:</strong> {change.source}</div>
                    <div><strong>Old Value:</strong> {change.old || 'N/A'}</div>
                    <div><strong>New Value:</strong> {change.new || 'N/A'}</div>
                    <div><strong>Date:</strong> {new Date(change.created_at).toLocaleString()}</div>
                    <div><strong>Reviewed:</strong> {change.reviewed ? 'Yes' : 'No'}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default ProductDetail;

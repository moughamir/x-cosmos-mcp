'use client';

import React, { useState, useEffect } from 'react';
import { Product } from '@/types/Product';
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Checkbox } from '@/components/ui/checkbox';

interface PipelineManagementProps {
  // Props if needed
}

const PipelineManagement: React.FC<PipelineManagementProps> = () => {
  const [taskType, setTaskType] = useState<string>('meta_optimization');
  const [allProducts, setAllProducts] = useState<Product[]>([]);
  const [selectedProductIds, setSelectedProductIds] = useState<Set<number>>(new Set());
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isLoadingProducts, setIsLoadingProducts] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchAllProducts = async () => {
    setIsLoadingProducts(true);
    setError(null);
    try {
      const response = await fetch('/api/products');
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      setAllProducts(data.products || []);
    } catch (e: any) {
      console.error('Error fetching all products:', e);
      setError(`Failed to load products: ${e.message}`);
    } finally {
      setIsLoadingProducts(false);
    }
  };

  useEffect(() => {
    fetchAllProducts();
  }, []);

  const handleTaskTypeChange = (value: string) => {
    setTaskType(value);
  };

  const handleProductSelection = (productId: number, checked: boolean) => {
    setSelectedProductIds(prev => {
      const newSet = new Set(prev);
      if (checked) {
        newSet.add(productId);
      } else {
        newSet.delete(productId);
      }
      return newSet;
    });
  };

  const runPipeline = async () => {
    if (!taskType) {
      alert('Please select a task type.');
      return;
    }

    setIsLoading(true);
    setError(null);

    const productIdsArray = Array.from(selectedProductIds);

    try {
      const response = await fetch('/api/pipeline/run', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          task_type: taskType,
          product_ids: productIdsArray
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      alert(`Pipeline run initiated for ${taskType}. Results: ${JSON.stringify(result.results)}`);
      setSelectedProductIds(new Set()); // Clear selection after run
    } catch (e: any) {
      console.error('Error running pipeline:', e);
      setError(`Failed to run pipeline: ${e.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Pipeline Management</CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {error && <p className="text-red-500">Error: {error}</p>}

        <div className="space-y-2">
          <Label htmlFor="taskType">Select Task Type:</Label>
          <Select value={taskType} onValueChange={handleTaskTypeChange}>
            <SelectTrigger>
              <SelectValue placeholder="Select a task type" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="meta_optimization">Meta Optimization</SelectItem>
              <SelectItem value="content_rewriting">Content Rewriting</SelectItem>
              <SelectItem value="keyword_analysis">Keyword Analysis</SelectItem>
              <SelectItem value="tag_optimization">Tag Optimization</SelectItem>
              <SelectItem value="category_normalization">Category Normalization</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-4">
          <Label>Select Products (optional, leave blank to process all):</Label>
          {isLoadingProducts ? (
            <p>Loading products...</p>
          ) : (
            <div className="max-h-48 overflow-y-auto border rounded-md p-4 space-y-2">
              {allProducts.map((product) => (
                <div key={product.id} className="flex items-center space-x-2">
                  <Checkbox
                    id={`product-${product.id}`}
                    checked={selectedProductIds.has(product.id)}
                    onCheckedChange={(checked) =>
                      handleProductSelection(product.id, checked as boolean)
                    }
                  />
                  <Label
                    htmlFor={`product-${product.id}`}
                    className="text-sm font-normal cursor-pointer"
                  >
                    {product.title} (ID: {product.id})
                  </Label>
                </div>
              ))}
            </div>
          )}
        </div>

        <Button
          onClick={runPipeline}
          disabled={isLoading}
          className="w-full"
        >
          {isLoading ? 'Running Pipeline...' : 'Run Pipeline'}
        </Button>
      </CardContent>
    </Card>
  );
};

export default PipelineManagement;

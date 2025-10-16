'use client';

import { useState, useEffect, ChangeEvent } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'; // shadcn/ui Select component
import { Label } from '@/components/ui/label'; // shadcn/ui Label component
import { Checkbox } from '@/components/ui/checkbox'; // shadcn/ui Checkbox component

import { Product } from '@/types/Product';

const PipelineManagementPage = () => {
  const [taskType, setTaskType] = useState<string>('meta_optimization');
  const [allProducts, setAllProducts] = useState<Product[]>([]);
  const [selectedProductIds, setSelectedProductIds] = useState<Set<number>>(new Set());
  const [isLoadingProducts, setIsLoadingProducts] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [isRunningPipeline, setIsRunningPipeline] = useState<boolean>(false);

  const fetchAllProducts = async () => {
    setIsLoadingProducts(true);
    setError(null);
    try {
      const response = await fetch('/api/products', { cache: 'no-store' });
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data: Product[] = await response.json();
      // Only fetch id and title as per original component's usage
      setAllProducts(data.map(p => ({ id: p.id, title: p.title, body_html: '', category: '', normalized_category: '', normalized_title: '', normalized_body_html: '', llm_confidence: 0, gmc_category_label: '' })));
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

  const handleProductSelection = (productId: number, isChecked: boolean) => {
    setSelectedProductIds((prev) => {
      const newSet = new Set(prev);
      if (isChecked) {
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

    const productIdsArray = Array.from(selectedProductIds);

    setIsRunningPipeline(true);
    setError(null);
    try {
      const response = await fetch('/api/pipeline/run', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          task_type: taskType,
          product_ids: productIdsArray,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || `HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      alert(`Pipeline run initiated for "${taskType}". Results: ${JSON.stringify(result.results)}`);
      setSelectedProductIds(new Set()); // Clear selection after successful run
    } catch (e: any) {
      console.error('Error running pipeline:', e);
      setError(`Failed to run pipeline: ${e.message}`);
    } finally {
      setIsRunningPipeline(false);
    }
  };

  return (
    <div className="container mx-auto p-4">
      <Card>
        <CardHeader>
          <CardTitle>Pipeline Management</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-6">
            {/* Task Type Selection */}
            <div>
              <Label htmlFor="taskType">Select Task Type</Label>
              <Select onValueChange={handleTaskTypeChange} defaultValue={taskType}>
                <SelectTrigger className="w-full">
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

            {/* Product Selection */}
            <div>
              <Label>Select Products (optional)</Label>
              <div className="mt-2 p-3 border rounded-md max-h-60 overflow-y-auto bg-background">
                {isLoadingProducts && <p>Loading products...</p>}
                {error && <p className="text-red-500">Error: {error}</p>}
                {!isLoadingProducts && !error && allProducts.length === 0 && (
                  <p>No products available.</p>
                )}
                {!isLoadingProducts && !error && allProducts.length > 0 && (
                  <div className="space-y-2">
                    {allProducts.map((product) => (
                      <div key={product.id} className="flex items-center space-x-2">
                        <Checkbox
                          id={`product-${product.id}`}
                          checked={selectedProductIds.has(product.id)}
                          onCheckedChange={(checked) => handleProductSelection(product.id, checked as boolean)}
                        />
                        <Label htmlFor={`product-${product.id}`}>
                          {product.title} (ID: {product.id})
                        </Label>
                      </div>
                    ))}
                  </div>
                )}
              </div>
              <p className="text-xs text-muted-foreground mt-2">
                Leave blank to process all products.
              </p>
            </div>
          </div>
        </CardContent>
        <CardFooter>
          <Button onClick={runPipeline} disabled={isRunningPipeline || !taskType}>
            {isRunningPipeline ? 'Running Pipeline...' : 'Run Pipeline'}
          </Button>
          {error && <p className="text-red-500 ml-4">Error: {error}</p>}
        </CardFooter>
      </Card>
    </div>
  );
};

export default PipelineManagementPage;

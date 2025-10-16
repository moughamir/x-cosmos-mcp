'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Skeleton } from '@/components/ui/skeleton';
import { toast } from "sonner";
import { Product } from '@/types/Product';

function ProductListSkeleton() {
  return (
    <div className="space-y-2">
      {[...Array(5)].map((_, i) => (
        <div key={i} className="flex items-center space-x-2">
          <Skeleton className="h-4 w-4" />
          <Skeleton className="h-4 w-5/6" />
        </div>
      ))}
    </div>
  );
}

export default function PipelineManagementPage() {
  const [taskType, setTaskType] = useState<string>('meta_optimization');
  const [allProducts, setAllProducts] = useState<Product[]>([]);
  const [selectedProductIds, setSelectedProductIds] = useState<Set<number>>(new Set());
  const [isLoadingProducts, setIsLoadingProducts] = useState<boolean>(true);
  const [isRunningPipeline, setIsRunningPipeline] = useState<boolean>(false);

  useEffect(() => {
    const fetchAllProducts = async () => {
      setIsLoadingProducts(true);
      try {
        const response = await fetch('/api/products', { cache: 'no-store' });
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data: { products: Product[] } = await response.json();
        setAllProducts(data.products);
      } catch (e) {
        console.error('Error fetching all products:', e);
        const errorMessage = e instanceof Error ? e.message : String(e);
        toast.error(`Failed to load products: ${errorMessage}`);
      } finally {
        setIsLoadingProducts(false);
      }
    };

    fetchAllProducts();
  }, []);

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
      toast.warning('Please select a task type.');
      return;
    }

    setIsRunningPipeline(true);
    try {
      const response = await fetch('/api/pipeline/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          task_type: taskType,
          product_ids: selectedProductIds.size > 0 ? Array.from(selectedProductIds) : null, // Send null if empty
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      toast.success(`Pipeline '${result.task_type}' initiated for ${result.product_count} products.`);
      setSelectedProductIds(new Set());
    } catch (e) {
      console.error('Error running pipeline:', e);
      const errorMessage = e instanceof Error ? e.message : String(e);
      toast.error(`Failed to run pipeline: ${errorMessage}`);
    } finally {
      setIsRunningPipeline(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Pipeline Management</CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        <div>
          <Label htmlFor="taskType">Select Task Type</Label>
          <Select onValueChange={setTaskType} defaultValue={taskType}>
            <SelectTrigger id="taskType" className="w-full">
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

        <div>
          <Label>Select Products (optional)</Label>
          <ScrollArea className="mt-2 h-72 w-full rounded-md border p-4">
            {isLoadingProducts ? (
              <ProductListSkeleton />
            ) : allProducts.length > 0 ? (
              <div className="space-y-2">
                {allProducts.map((product) => (
                  <div key={product.id} className="flex items-center space-x-2">
                    <Checkbox
                      id={`product-${product.id}`}
                      checked={selectedProductIds.has(product.id)}
                      onCheckedChange={(checked) => handleProductSelection(product.id, checked as boolean)}
                    />
                    <Label htmlFor={`product-${product.id}`} className="font-normal">
                      {product.title} (ID: {product.id})
                    </Label>
                  </div>
                ))}
              </div>
            ) : (
              <p>No products available.</p>
            )}
          </ScrollArea>
          <p className="text-xs text-muted-foreground mt-2">
            If no products are selected, the pipeline will run on all products.
          </p>
        </div>
      </CardContent>
      <CardFooter>
        <Button onClick={runPipeline} disabled={isRunningPipeline || !taskType}>
          {isRunningPipeline ? 'Running Pipeline...' : 'Run Pipeline'}
        </Button>
      </CardFooter>
    </Card>
  );
}

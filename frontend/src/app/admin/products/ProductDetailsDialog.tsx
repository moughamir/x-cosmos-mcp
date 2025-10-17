'use client';

import { useState, useEffect, JSX } from 'react';
import { Product } from '@/types/Product';
import { fetchApi } from '@/lib/api';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import Image from 'next/image';

interface ProductDetailsDialogProps {
  productId: number | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function ProductDetailsDialog({ productId, open, onOpenChange }: ProductDetailsDialogProps): JSX.Element {
  const [product, setProduct] = useState<Product | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (open && productId) {
      loadProductDetails();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, productId]);

  const loadProductDetails = async () => {
    if (!productId) return;

    setLoading(true);
    setError(null);

    try {
      const res = await fetchApi(`/api/products/${productId}`);
      if (!res.ok) {
        throw new Error('Failed to fetch product details');
      }
      const data = await res.json();
      setProduct(data.product);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh]">
        <DialogHeader>
          <DialogTitle>
            {loading ? 'Loading...' : (product?.title || 'Product Details')}
          </DialogTitle>
          <DialogDescription>
            {loading ? 'Loading product details...' : `Product ID: ${productId}`}
          </DialogDescription>
        </DialogHeader>

        {error && (
          <div className="text-red-500 text-sm p-4 bg-red-50 rounded">
            {error}
          </div>
        )}

        {loading ? (
          <div className="space-y-4">
            <Skeleton className="h-64 w-full" />
            <Skeleton className="h-32 w-full" />
          </div>
        ) : product ? (
          <ScrollArea className="h-[calc(90vh-120px)] pr-4">
            <Tabs defaultValue="overview" className="w-full">
              <TabsList className="grid w-full grid-cols-4">
                <TabsTrigger value="overview">Overview</TabsTrigger>
                <TabsTrigger value="images">Images</TabsTrigger>
                <TabsTrigger value="variants">Variants</TabsTrigger>
                <TabsTrigger value="details">Details</TabsTrigger>
              </TabsList>

              <TabsContent value="overview" className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <h3 className="text-sm font-medium text-gray-500">Vendor</h3>
                    <p className="text-base">{product.vendor_name || 'N/A'}</p>
                  </div>
                  <div>
                    <h3 className="text-sm font-medium text-gray-500">Product Type</h3>
                    <p className="text-base">{product.product_type_name || 'N/A'}</p>
                  </div>
                  <div>
                    <h3 className="text-sm font-medium text-gray-500">Category</h3>
                    <p className="text-base">{product.gmc_category_label || 'N/A'}</p>
                  </div>
                  <div>
                    <h3 className="text-sm font-medium text-gray-500">Confidence Score</h3>
                    <p className="text-base">
                      {product.llm_confidence ? (
                        <Badge variant={product.llm_confidence > 0.8 ? 'default' : 'secondary'}>
                          {(product.llm_confidence * 100).toFixed(1)}%
                        </Badge>
                      ) : 'N/A'}
                    </p>
                  </div>
                </div>

                <Separator />

                {product.tags && product.tags.length > 0 && (
                  <div>
                    <h3 className="text-sm font-medium text-gray-500 mb-2">Tags</h3>
                    <div className="flex flex-wrap gap-2">
                      {product.tags.map((tag, idx) => (
                        <Badge key={idx} variant="outline">{tag}</Badge>
                      ))}
                    </div>
                  </div>
                )}

                {product.body_html && (
                  <div>
                    <h3 className="text-sm font-medium text-gray-500 mb-2">Description</h3>
                    <div
                      className="prose prose-sm max-w-none"
                      dangerouslySetInnerHTML={{ __html: product.body_html }}
                    />
                  </div>
                )}
              </TabsContent>

              <TabsContent value="images" className="space-y-4">
                {product.images && Array.isArray(product.images) && product.images.length > 0 ? (
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                    {product.images
                      .sort((a, b) => a.position - b.position)
                      .map((image) => (
                        <div key={image.id} className="relative aspect-square border rounded-lg overflow-hidden">
                          <Image
                            src={image.src}
                            alt={`Product image ${image.position}`}
                            fill
                            className="object-cover"
                            sizes="(max-width: 768px) 50vw, 33vw"
                          />
                          <div className="absolute bottom-0 left-0 right-0 bg-black/50 text-white text-xs p-1 text-center">
                            Position: {image.position}
                          </div>
                        </div>
                      ))}
                  </div>
                ) : (
                  <p className="text-gray-500 text-center py-8">No images available</p>
                )}
              </TabsContent>

              <TabsContent value="variants" className="space-y-4">
                {product.variants && Array.isArray(product.variants) && product.variants.length > 0 ? (
                  <div className="space-y-4">
                    {product.options && Array.isArray(product.options) && product.options.length > 0 && (
                      <div className="bg-gray-50 p-4 rounded-lg">
                        <h3 className="text-sm font-medium mb-2">Options</h3>
                        <div className="space-y-2">
                          {product.options
                            .sort((a, b) => a.position - b.position)
                            .map((option) => (
                              <div key={option.id}>
                                <span className="font-medium text-sm">{option.name}:</span>{' '}
                                <span className="text-sm text-gray-600">
                                  {option.values.join(', ')}
                                </span>
                              </div>
                            ))}
                        </div>
                      </div>
                    )}

                    <div className="space-y-3">
                      {product.variants.map((variant) => (
                        <div key={variant.id} className="border rounded-lg p-4">
                          <div className="flex justify-between items-start mb-2">
                            <h4 className="font-medium">{variant.title}</h4>
                            <Badge variant="default" className="text-lg">
                              ${parseFloat(variant.price).toFixed(2)}
                            </Badge>
                          </div>
                          <div className="grid grid-cols-2 gap-2 text-sm text-gray-600">
                            {variant.sku && (
                              <div>
                                <span className="font-medium">SKU:</span> {variant.sku}
                              </div>
                            )}
                            {variant.option1 && (
                              <div>
                                <span className="font-medium">Option 1:</span> {variant.option1}
                              </div>
                            )}
                            {variant.option2 && (
                              <div>
                                <span className="font-medium">Option 2:</span> {variant.option2}
                              </div>
                            )}
                            {variant.option3 && (
                              <div>
                                <span className="font-medium">Option 3:</span> {variant.option3}
                              </div>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <p className="text-gray-500 text-center py-8">No variants available</p>
                )}
              </TabsContent>

              <TabsContent value="details" className="space-y-4">
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <h3 className="font-medium text-gray-500">Product ID</h3>
                    <p>{product.id}</p>
                  </div>
                  <div>
                    <h3 className="font-medium text-gray-500">Vendor ID</h3>
                    <p>{product.vendor_id || 'N/A'}</p>
                  </div>
                  <div>
                    <h3 className="font-medium text-gray-500">Product Type ID</h3>
                    <p>{product.product_type_id || 'N/A'}</p>
                  </div>
                  <div>
                    <h3 className="font-medium text-gray-500">Created At</h3>
                    <p>{product.created_at ? new Date(product.created_at).toLocaleString() : 'N/A'}</p>
                  </div>
                  <div>
                    <h3 className="font-medium text-gray-500">Updated At</h3>
                    <p>{product.updated_at ? new Date(product.updated_at).toLocaleString() : 'N/A'}</p>
                  </div>
                  <div>
                    <h3 className="font-medium text-gray-500">Normalized Category</h3>
                    <p>{product.normalized_category || 'N/A'}</p>
                  </div>
                </div>

                {product.normalized_title && (
                  <div>
                    <h3 className="font-medium text-gray-500 mb-1">Normalized Title</h3>
                    <p className="text-sm">{product.normalized_title}</p>
                  </div>
                )}

                {product.normalized_body_html && (
                  <div>
                    <h3 className="font-medium text-gray-500 mb-1">Normalized Description</h3>
                    <div
                      className="prose prose-sm max-w-none text-sm"
                      dangerouslySetInnerHTML={{ __html: product.normalized_body_html }}
                    />
                  </div>
                )}
              </TabsContent>
            </Tabs>
          </ScrollArea>
        ) : null}
      </DialogContent>
    </Dialog>
  );
}

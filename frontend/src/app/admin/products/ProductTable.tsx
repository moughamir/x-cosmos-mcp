'use client';

import { useState } from 'react';
import { Product } from '@/types/Product';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Pagination,
  PaginationContent,
  PaginationEllipsis,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
} from "@/components/ui/pagination";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ProductDetailsDialog } from './ProductDetailsDialog';
import { Search, Filter } from 'lucide-react';

interface ProductTableProps {
  products: Product[];
  total: number;
  page: number;
  limit: number;
  totalPages: number;
  onPageChange: (page: number) => void;
  onLimitChange: (limit: number) => void;
  onSearchChange: (search: string) => void;
  onCategoryChange: (category: string) => void;
  onConfidenceChange: (min: number | null, max: number | null) => void;
}

export function ProductTable({
  products,
  total,
  page,
  limit,
  totalPages,
  onPageChange,
  onLimitChange,
  onSearchChange,
  onCategoryChange,
  onConfidenceChange,
}: ProductTableProps) {
  const [selectedProductId, setSelectedProductId] = useState<number | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [searchValue, setSearchValue] = useState('');
  const [categoryValue, setCategoryValue] = useState('');
  const [confidenceFilter, setConfidenceFilter] = useState<string>('all');

  const handleSearch = (value: string) => {
    setSearchValue(value);
    onSearchChange(value);
  };

  const handleCategoryFilter = (value: string) => {
    setCategoryValue(value);
    onCategoryChange(value);
  };

  const handleConfidenceFilter = (value: string) => {
    setConfidenceFilter(value);
    switch (value) {
      case 'high':
        onConfidenceChange(0.8, null);
        break;
      case 'medium':
        onConfidenceChange(0.5, 0.8);
        break;
      case 'low':
        onConfidenceChange(null, 0.5);
        break;
      default:
        onConfidenceChange(null, null);
    }
  };

  const handleViewDetails = (productId: number) => {
    setSelectedProductId(productId);
    setDialogOpen(true);
  };

  const renderPaginationItems = () => {
    const items = [];
    const maxVisible = 5;

    let startPage = Math.max(1, page - Math.floor(maxVisible / 2));
    let endPage = Math.min(totalPages, startPage + maxVisible - 1);

    if (endPage - startPage < maxVisible - 1) {
      startPage = Math.max(1, endPage - maxVisible + 1);
    }

    if (startPage > 1) {
      items.push(
        <PaginationItem key="1">
          <PaginationLink onClick={() => onPageChange(1)}>1</PaginationLink>
        </PaginationItem>
      );
      if (startPage > 2) {
        items.push(<PaginationEllipsis key="ellipsis-start" />);
      }
    }

    for (let i = startPage; i <= endPage; i++) {
      items.push(
        <PaginationItem key={i}>
          <PaginationLink
            onClick={() => onPageChange(i)}
            isActive={i === page}
          >
            {i}
          </PaginationLink>
        </PaginationItem>
      );
    }

    if (endPage < totalPages) {
      if (endPage < totalPages - 1) {
        items.push(<PaginationEllipsis key="ellipsis-end" />);
      }
      items.push(
        <PaginationItem key={totalPages}>
          <PaginationLink onClick={() => onPageChange(totalPages)}>
            {totalPages}
          </PaginationLink>
        </PaginationItem>
      );
    }

    return items;
  };

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
          <Input
            placeholder="Search products..."
            value={searchValue}
            onChange={(e) => handleSearch(e.target.value)}
            className="pl-10"
          />
        </div>
        <div className="w-full sm:w-48">
          <Input
            placeholder="Filter by category..."
            value={categoryValue}
            onChange={(e) => handleCategoryFilter(e.target.value)}
          />
        </div>
        <Select value={confidenceFilter} onValueChange={handleConfidenceFilter}>
          <SelectTrigger className="w-full sm:w-48">
            <SelectValue placeholder="Confidence" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Confidence</SelectItem>
            <SelectItem value="high">High (&gt; 80%)</SelectItem>
            <SelectItem value="medium">Medium (50-80%)</SelectItem>
            <SelectItem value="low">Low (&lt; 50%)</SelectItem>
          </SelectContent>
        </Select>
        <Select value={limit.toString()} onValueChange={(val) => onLimitChange(parseInt(val))}>
          <SelectTrigger className="w-full sm:w-32">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="10">10 / page</SelectItem>
            <SelectItem value="25">25 / page</SelectItem>
            <SelectItem value="50">50 / page</SelectItem>
            <SelectItem value="100">100 / page</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Results count */}
      <div className="text-sm text-gray-600">
        Showing {products.length > 0 ? (page - 1) * limit + 1 : 0} to{' '}
        {Math.min(page * limit, total)} of {total} products
      </div>

      {/* Table */}
      {products.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          <Filter className="mx-auto h-12 w-12 mb-4 text-gray-300" />
          <p>No products found.</p>
        </div>
      ) : (
        <div className="border rounded-lg">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-20">ID</TableHead>
                <TableHead>Title</TableHead>
                <TableHead className="w-32">Confidence</TableHead>
                <TableHead>Category</TableHead>
                <TableHead className="w-32">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {products.map((product) => (
                <TableRow key={product.id}>
                  <TableCell className="font-mono text-sm">{product.id}</TableCell>
                  <TableCell className="font-medium">{product.title}</TableCell>
                  <TableCell>
                    {product.llm_confidence ? (
                      <Badge
                        variant={
                          product.llm_confidence > 0.8
                            ? 'default'
                            : product.llm_confidence > 0.5
                            ? 'secondary'
                            : 'destructive'
                        }
                      >
                        {(product.llm_confidence * 100).toFixed(0)}%
                      </Badge>
                    ) : (
                      <span className="text-gray-400">N/A</span>
                    )}
                  </TableCell>
                  <TableCell className="text-sm text-gray-600">
                    {product.gmc_category_label || 'N/A'}
                  </TableCell>
                  <TableCell>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleViewDetails(product.id)}
                    >
                      View
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <Pagination>
          <PaginationContent>
            <PaginationItem>
              <PaginationPrevious
                onClick={() => page > 1 && onPageChange(page - 1)}
                className={page === 1 ? 'pointer-events-none opacity-50' : 'cursor-pointer'}
              />
            </PaginationItem>
            {renderPaginationItems()}
            <PaginationItem>
              <PaginationNext
                onClick={() => page < totalPages && onPageChange(page + 1)}
                className={page === totalPages ? 'pointer-events-none opacity-50' : 'cursor-pointer'}
              />
            </PaginationItem>
          </PaginationContent>
        </Pagination>
      )}

      {/* Product Details Dialog */}
      <ProductDetailsDialog
        productId={selectedProductId}
        open={dialogOpen}
        onOpenChange={setDialogOpen}
      />
    </div>
  );
}

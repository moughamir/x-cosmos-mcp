'use client';

import React, { useState, useEffect } from 'react';
import { TaxonomyNode } from '@/types/TaxonomyNode';
import { Button } from '@/components/ui/button'; // Assuming Button is available
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'; // For layout

// Define the structure for the fetched taxonomy tree
interface TaxonomyTree {
  [key: string]: TaxonomyNode;
}

interface TaxonomyBrowserProps {
  // You might pass an initial tree or fetch it here
  // For now, we'll fetch it internally
}

const TaxonomyBrowser: React.FC<TaxonomyBrowserProps> = () => {
  const [taxonomyTree, setTaxonomyTree] = useState<TaxonomyTree>({});
  const [expandedNodes, setExpandedNodes] = useState<Set<string>>(new Set());
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchTaxonomyTree = async () => {
    setIsLoading(true);
    setError(null);
    try {
      // Fetch from the backend API
      const response = await fetch('/api/taxonomy/tree', { cache: 'no-store' }); // Use no-store for dynamic data
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data: TaxonomyTree = await response.json();
      setTaxonomyTree(data);
    } catch (e: any) {
      console.error('Error fetching taxonomy tree:', e);
      setError(`Failed to load taxonomy tree: ${e.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchTaxonomyTree();
  }, []);

  const toggleNode = (fullPath: string) => {
    setExpandedNodes((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(fullPath)) {
        newSet.delete(fullPath);
      } else {
        newSet.add(fullPath);
      }
      return newSet;
    });
  };

  const renderNode = (node: TaxonomyNode, level: number = 0) => {
    const hasChildren = Object.keys(node.children).length > 0;
    const isExpanded = expandedNodes.has(node.full_path);
    const indentStyle = { paddingLeft: `${level * 1.5}rem` }; // Indent based on level

    return (
      <li key={node.full_path} className="mb-2">
        <div className="flex items-center">
          {hasChildren && (
            <Button
              variant="ghost"
              size="icon"
              onClick={() => toggleNode(node.full_path)}
              className="mr-2 h-6 w-6 p-0"
              aria-label={isExpanded ? 'Collapse node' : 'Expand node'}
            >
              {isExpanded ? '▼' : '►'}
            </Button>
          )}
          {!hasChildren && (
            <div className="mr-2 w-6 h-6 flex items-center justify-center"></div> // Placeholder for alignment
          )}
          <span
            className={`cursor-pointer font-medium ${hasChildren ? 'text-primary' : 'text-gray-700'}`}
            onClick={() => hasChildren && toggleNode(node.full_path)}
          >
            {node.name}
          </span>
          <span className="text-xs text-gray-500 ml-2">({node.full_path})</span>
        </div>
        {isExpanded && hasChildren && (
          <ul className="mt-1">
            {Object.values(node.children).map((child) =>
              renderNode(child, level + 1)
            )}
          </ul>
        )}
      </li>
    );
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Google Product Taxonomy Browser</CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading && <p>Loading taxonomy tree...</p>}
        {error && <p className="text-red-500">Error: {error}</p>}
        {!isLoading && !error && Object.keys(taxonomyTree).length === 0 && (
          <p>No taxonomy data available.</p>
        )}
        {!isLoading && !error && Object.keys(taxonomyTree).length > 0 && (
          <ul className="space-y-2">
            {Object.values(taxonomyTree).map((rootNode) =>
              renderNode(rootNode, 0)
            )}
          </ul>
        )}
      </CardContent>
    </Card>
  );
};

export default TaxonomyBrowser;

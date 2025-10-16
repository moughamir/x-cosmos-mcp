'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { toast } from "sonner";
import { TaxonomyNode } from '@/types/TaxonomyNode';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { ChevronRight } from "lucide-react";

function TaxonomyTree({ nodes }: { nodes: TaxonomyNode[] }) {
  if (!nodes || nodes.length === 0) return null;

  return (
    <div className="space-y-1">
      {nodes.map((node) => (
        <Collapsible key={node.id}>
          <div className="flex items-center space-x-2">
            {node.children && node.children.length > 0 && (
              <CollapsibleTrigger asChild>
                <Button variant="ghost" size="sm" className="w-9 p-0">
                  <ChevronRight className="h-4 w-4 transition-transform data-[state=open]:rotate-90" />
                  <span className="sr-only">Toggle</span>
                </Button>
              </CollapsibleTrigger>
            )}
            <p className={`pl-${node.children && node.children.length > 0 ? '0' : '9'}`}>{node.name}</p>
          </div>
          <CollapsibleContent className="pl-4 border-l ml-4">
            <TaxonomyTree nodes={node.children} />
          </CollapsibleContent>
        </Collapsible>
      ))}
    </div>
  );
}

export default function TaxonomyPage() {
  const [taxonomies, setTaxonomies] = useState<string[]>([]);
  const [selectedTaxonomy, setSelectedTaxonomy] = useState<string | null>(null);
  const [taxonomyData, setTaxonomyData] = useState<TaxonomyNode[]>([]);
  const [isLoadingList, setIsLoadingList] = useState<boolean>(true);
  const [isLoadingTree, setIsLoadingTree] = useState<boolean>(false);

  useEffect(() => {
    const fetchTaxonomies = async () => {
      setIsLoadingList(true);
      try {
        const response = await fetch('/api/taxonomy');
        if (!response.ok) throw new Error('Failed to fetch taxonomy list');
        const data: { files: string[] } = await response.json();
        setTaxonomies(data.files);
        if (data.files.length > 0) {
          setSelectedTaxonomy(data.files[0]);
        }
      } catch (e: any) {
        toast.error(`Failed to load taxonomies: ${e.message}`);
      } finally {
        setIsLoadingList(false);
      }
    };
    fetchTaxonomies();
  }, []);

  useEffect(() => {
    if (!selectedTaxonomy) return;

    const fetchTaxonomyData = async () => {
      setIsLoadingTree(true);
      try {
        const response = await fetch(`/api/taxonomy/${selectedTaxonomy}`);
        if (!response.ok) throw new Error('Failed to fetch taxonomy data');
        const data: { tree: TaxonomyNode[] } = await response.json();
        setTaxonomyData(data.tree);
      } catch (e: any) {
        toast.error(`Failed to load taxonomy data: ${e.message}`);
        setTaxonomyData([]);
      } finally {
        setIsLoadingTree(false);
      }
    };
    fetchTaxonomyData();
  }, [selectedTaxonomy]);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Taxonomy Viewer</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {isLoadingList ? (
          <Skeleton className="h-10 w-1/2" />
        ) : (
          <Select onValueChange={setSelectedTaxonomy} value={selectedTaxonomy ?? ''}>
            <SelectTrigger>
              <SelectValue placeholder="Select a taxonomy file" />
            </SelectTrigger>
            <SelectContent>
              {taxonomies.map((file) => (
                <SelectItem key={file} value={file}>{file}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}

        <div className="border rounded-md p-4 min-h-[400px]">
          {isLoadingTree ? (
            <div className="space-y-2">
              {[...Array(10)].map((_, i) => <Skeleton key={i} className="h-6 w-full" />)}
            </div>
          ) : (
            <TaxonomyTree nodes={taxonomyData} />
          )}
        </div>
      </CardContent>
    </Card>
  );
}

'use client';

import { useState, useEffect, FormEvent } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
import { toast } from "sonner";
import { OllamaModel } from '@/types/OllamaModel';

function ModelListSkeleton() {
  return (
    <div className="space-y-4">
      {[...Array(3)].map((_, i) => (
        <Card key={i} className="p-4">
          <div className="flex justify-between items-center">
            <div>
              <Skeleton className="h-6 w-40 mb-2" />
              <Skeleton className="h-4 w-24" />
            </div>
            <Skeleton className="h-4 w-32" />
          </div>
        </Card>
      ))}
    </div>
  );
}

export default function ModelManagementPage() {
  const [models, setModels] = useState<OllamaModel[]>([]);
  const [modelToPull, setModelToPull] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isPulling, setIsPulling] = useState<boolean>(false);

  const fetchModels = async () => {
    setIsLoading(true);
    try {
      console.log("Fetching models from /api/ollama/models");
      const response = await fetch('/api/ollama/models', { cache: 'no-store' });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
      }
      const data: { models: OllamaModel[] } = await response.json();
      setModels(data.models);
    } catch (e) {
      console.error('Error fetching Ollama models:', e);
      const errorMessage = e instanceof Error ? e.message : String(e);
      toast.error(`Failed to load Ollama models: ${errorMessage}`);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchModels();
  }, []);

  const handlePullSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!modelToPull) return;

    setIsPulling(true);
    toast.info(`Starting to pull model: ${modelToPull}...`);
    try {
      const response = await fetch('/api/ollama/pull', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model_name: modelToPull }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
      }

      toast.success(`Successfully initiated pull for model: ${modelToPull}`);
      setModelToPull('');
      // Optionally, you could implement a mechanism to stream pull status
      // For now, we just refresh the list after a delay to allow the model to appear
      setTimeout(() => fetchModels(), 5000);
    } catch (e) {
      console.error('Error pulling model:', e);
      const errorMessage = e instanceof Error ? e.message : String(e);
      toast.error(`Failed to pull model: ${errorMessage}`);
    } finally {
      setIsPulling(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Ollama Model Management</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handlePullSubmit} className="flex items-center gap-2 mb-6">
          <Input
            type="text"
            placeholder="Enter model name to pull (e.g., llama3:8b)"
            value={modelToPull}
            onChange={(e) => setModelToPull(e.target.value)}
            className="flex-grow"
          />
          <Button type="submit" disabled={isPulling || !modelToPull}>
            {isPulling ? 'Pulling...' : 'Pull Model'}
          </Button>
        </form>

        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-semibold">Available Models</h2>
          <Button onClick={fetchModels} variant="outline" disabled={isLoading}>
            Refresh
          </Button>
        </div>

        {isLoading ? (
          <ModelListSkeleton />
        ) : models.length === 0 ? (
          <p>No Ollama models found. Ensure Ollama is running and pull a model to get started.</p>
        ) : (
          <div className="space-y-4">
            {models.map((model) => (
              <Card key={model.name} className="p-4">
                <div className="flex justify-between items-start">
                  <div>
                    <p className="font-semibold text-lg">{model.name}</p>
                    <p className="text-sm text-muted-foreground">
                      Size: {(model.size / 1e9).toFixed(2)} GB
                    </p>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    Modified: {new Date(model.modified_at).toLocaleString()}
                  </p>
                </div>
              </Card>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

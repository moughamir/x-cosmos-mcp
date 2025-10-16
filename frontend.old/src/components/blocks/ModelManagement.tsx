'use client';

import React, { useState, useEffect } from 'react';
import { OllamaModel } from '@/types/OllamaModel';
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

interface ModelManagementProps {
  // Props if needed
}

const ModelManagement: React.FC<ModelManagementProps> = () => {
  const [models, setModels] = useState<OllamaModel[]>([]);
  const [modelToPull, setModelToPull] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isLoadingModels, setIsLoadingModels] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchModels = async () => {
    setIsLoadingModels(true);
    setError(null);
    try {
      const response = await fetch('/api/ollama/models');
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      setModels(data || []);
    } catch (e: any) {
      console.error('Error fetching Ollama models:', e);
      setError(`Failed to fetch models: ${e.message}`);
    } finally {
      setIsLoadingModels(false);
    }
  };

  useEffect(() => {
    fetchModels();
  }, []);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setModelToPull(e.target.value);
  };

  const pullModel = async () => {
    if (!modelToPull.trim()) {
      alert('Please enter a model name to pull.');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/ollama/pull', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ model_name: modelToPull.trim() })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      alert(`Model ${modelToPull} pull initiated.`);
      setModelToPull(''); // Clear input
      await fetchModels(); // Refresh list
    } catch (e: any) {
      console.error('Error pulling model:', e);
      setError(`Failed to pull model: ${e.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const formatFileSize = (bytes: number) => {
    return (bytes / (1024 * 1024 * 1024)).toFixed(2) + ' GB';
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Ollama Model Management</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {error && <p className="text-red-500">Error: {error}</p>}

        <div className="flex gap-2">
          <div className="flex-1">
            <Label htmlFor="modelInput" className="sr-only">
              Model name to pull
            </Label>
            <Input
              id="modelInput"
              type="text"
              placeholder="Enter model name to pull (e.g., llama2)"
              value={modelToPull}
              onChange={handleInputChange}
            />
          </div>
          <Button onClick={pullModel} disabled={isLoading}>
            Pull Model
          </Button>
        </div>

        <Button
          onClick={fetchModels}
          disabled={isLoadingModels}
          variant="outline"
          className="w-full"
        >
          {isLoadingModels ? 'Refreshing...' : 'Refresh Models'}
        </Button>

        <div className="space-y-3">
          {models.length === 0 ? (
            <p className="text-gray-500">
              No Ollama models found. Ensure Ollama is running and models are pulled.
            </p>
          ) : (
            models.map((model) => (
              <div
                key={model.name}
                className="border rounded-lg p-4 bg-gray-50"
              >
                <div className="flex justify-between items-start">
                  <div>
                    <h3 className="font-semibold text-lg">{model.name}</h3>
                    <p className="text-sm text-gray-600">
                      Size: {formatFileSize(model.size)}
                    </p>
                    <p className="text-sm text-gray-600">
                      Modified: {new Date(model.modified_at).toLocaleString()}
                    </p>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </CardContent>
    </Card>
  );
};

export default ModelManagement;

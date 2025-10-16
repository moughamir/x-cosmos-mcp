'use client';

import { useState, useEffect, ChangeEvent } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { OllamaModel } from '@/types/OllamaModel';

const ModelManagementPage = () => {
  const [models, setModels] = useState<OllamaModel[]>([]);
  const [modelToPull, setModelToPull] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [isPulling, setIsPulling] = useState<boolean>(false);

  const fetchModels = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch('/api/ollama/models', { cache: 'no-store' });
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data: OllamaModel[] = await response.json();
      setModels(data);
    } catch (e: any) {
      console.error('Error fetching Ollama models:', e);
      setError(`Failed to load Ollama models: ${e.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchModels();
  }, []);

  const handleInputChange = (e: ChangeEvent<HTMLInputElement>) => {
    setModelToPull(e.target.value);
  };

  const pullModel = async () => {
    if (!modelToPull) return;
    setIsPulling(true);
    setError(null);
    try {
      const response = await fetch('/api/ollama/pull', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ model_name: modelToPull }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || `HTTP error! status: ${response.status}`);
      }

      alert(`Model "${modelToPull}" pull initiated.`);
      setModelToPull(''); // Clear input
      fetchModels(); // Refresh list to show the new model (or its status)
    } catch (e: any) {
      console.error('Error pulling model:', e);
      setError(`Failed to pull model: ${e.message}`);
    } finally {
      setIsPulling(false);
    }
  };

  return (
    <div className="container mx-auto p-4">
      <Card>
        <CardHeader>
          <CardTitle>Ollama Model Management</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col sm:flex-row gap-4 mb-6">
            <div className="flex-grow">
              <Input
                type="text"
                placeholder="Enter model name to pull (e.g., llama2)"
                value={modelToPull}
                onChange={handleInputChange}
              />
            </div>
            <Button onClick={pullModel} disabled={isPulling || !modelToPull}>
              {isPulling ? 'Pulling...' : 'Pull Model'}
            </Button>
          </div>

          <Button onClick={fetchModels} variant="outline" disabled={isLoading} className="mb-6">
            Refresh Models
          </Button>

          <h2 className="text-xl font-bold mb-3">Available Models</h2>
          {isLoading && <p>Loading models...</p>}
          {error && <p className="text-red-500">Error: {error}</p>}
          {!isLoading && !error && models.length === 0 && (
            <p>
              No Ollama models found. Ensure Ollama is running and models are pulled.
            </p>
          )}
          {!isLoading && !error && models.length > 0 && (
            <div className="space-y-4">
              {models.map((model) => (
                <Card key={model.name} className="model-card p-4">
                  <CardContent className="p-0 flex-grow">
                    <div className="flex justify-between items-center">
                      <div>
                        <p className="font-semibold text-lg">{model.name}</p>
                        <p className="text-sm text-gray-600">
                          Size: {(model.size / (1024 * 1024 * 1024)).toFixed(2)} GB
                        </p>
                        <p className="text-sm text-gray-600">
                          Modified: {new Date(model.modified_at).toLocaleString()}
                        </p>
                      </div>
                      {/* Add a button here if you want to add actions per model, e.g., delete */}
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default ModelManagementPage;

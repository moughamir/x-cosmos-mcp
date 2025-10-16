'use client';

import React, { useState, useEffect } from 'react';
import { PromptFile } from '@/types/PromptFile';
import { PromptContent } from '@/types/PromptContent';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';

interface PromptManagementProps {
  // Props if needed
}

const PromptManagement: React.FC<PromptManagementProps> = () => {
  const [promptFiles, setPromptFiles] = useState<PromptFile[]>([]);
  const [selectedPrompt, setSelectedPrompt] = useState<PromptContent | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchPromptFiles = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch('/api/prompts');
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      setPromptFiles(data.prompts.map((name: string) => ({ name })) || []);
    } catch (e: any) {
      console.error('Error fetching prompt files:', e);
      setError(`Failed to fetch prompts: ${e.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchPromptFiles();
  }, []);

  const selectPrompt = async (promptName: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch(`/api/prompts/${promptName}`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      setSelectedPrompt(data);
    } catch (e: any) {
      console.error(`Error fetching prompt ${promptName}:`, e);
      setError(`Failed to fetch prompt: ${e.message}`);
      setSelectedPrompt(null);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Prompt Management</CardTitle>
        </CardHeader>
        <CardContent>
          {error && <p className="text-red-500 mb-4">Error: {error}</p>}

          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 mb-6">
            {promptFiles.length === 0 ? (
              <p className="col-span-full text-gray-500">No prompt files found.</p>
            ) : (
              promptFiles.map((prompt) => (
                <div
                  key={prompt.name}
                  className={`p-4 rounded-lg border cursor-pointer transition-colors ${
                    selectedPrompt?.name === prompt.name
                      ? 'bg-blue-500 text-white border-blue-500'
                      : 'bg-gray-50 hover:bg-gray-100 border-gray-200'
                  }`}
                  onClick={() => selectPrompt(prompt.name)}
                >
                  <h3 className="font-medium truncate" title={prompt.name}>
                    {prompt.name}
                  </h3>
                </div>
              ))
            )}
          </div>

          {selectedPrompt && (
            <div className="space-y-2">
              <h2 className="text-lg font-semibold">{selectedPrompt.name} Content</h2>
              <div className="bg-gray-50 border rounded-lg p-4 font-mono text-sm whitespace-pre-wrap max-h-96 overflow-y-auto">
                {selectedPrompt.content}
              </div>
            </div>
          )}

          {!selectedPrompt && !error && (
            <p className="text-gray-500">Select a prompt to view its content.</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default PromptManagement;

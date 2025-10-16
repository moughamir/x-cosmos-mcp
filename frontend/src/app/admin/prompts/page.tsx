'use client';

import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from '@/components/ui/card';
import { PromptFile } from '@/types/PromptFile';
import { PromptContent } from '@/types/PromptContent';

const PromptManagementPage = () => {
  const [promptFiles, setPromptFiles] = useState<PromptFile[]>([]);
  const [selectedPrompt, setSelectedPrompt] = useState<PromptContent | null>(null);
  const [isLoadingFiles, setIsLoadingFiles] = useState<boolean>(true);
  const [isLoadingContent, setIsLoadingContent] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchPromptFiles = async () => {
    setIsLoadingFiles(true);
    setError(null);
    try {
      const response = await fetch('/api/prompts', { cache: 'no-store' });
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      setPromptFiles(data.prompts.map((name: string) => ({ name })));
    } catch (e: any) {
      console.error('Error fetching prompt files:', e);
      setError(`Failed to load prompt files: ${e.message}`);
    } finally {
      setIsLoadingFiles(false);
    }
  };

  useEffect(() => {
    fetchPromptFiles();
  }, []);

  const selectPrompt = async (promptName: string) => {
    setIsLoadingContent(true);
    setError(null);
    try {
      const response = await fetch(`/api/prompts/${promptName}`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data: PromptContent = await response.json();
      setSelectedPrompt(data);
    } catch (e: any) {
      console.error(`Error fetching prompt ${promptName}:`, e);
      setError(`Failed to load prompt content: ${e.message}`);
      setSelectedPrompt(null);
    } finally {
      setIsLoadingContent(false);
    }
  };

  return (
    <div className="container mx-auto p-4">
      <Card>
        <CardHeader>
          <CardTitle>Prompt Management</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Prompt List Column */}
            <div className="col-span-1 md:col-span-1">
              <h2 className="text-lg font-semibold mb-3">Available Prompts</h2>
              {isLoadingFiles && <p>Loading prompts...</p>}
              {error && <p className="text-red-500">Error: {error}</p>}
              {!isLoadingFiles && !error && promptFiles.length === 0 && (
                <p>No prompt files found.</p>
              )}
              {!isLoadingFiles && !error && promptFiles.length > 0 && (
                <ul className="space-y-2">
                  {promptFiles.map((prompt) => (
                    <li
                      key={prompt.name}
                      className={`p-3 rounded-md cursor-pointer transition-colors ${
                        selectedPrompt?.name === prompt.name
                          ? 'bg-primary text-primary-foreground shadow-sm'
                          : 'bg-secondary hover:bg-secondary/80'
                      }`}
                      onClick={() => selectPrompt(prompt.name)}
                    >
                      {prompt.name}
                    </li>
                  ))}
                </ul>
              )}
            </div>

            {/* Prompt Content Column */}
            <div className="col-span-1 md:col-span-2">
              <h2 className="text-lg font-semibold mb-3">
                {selectedPrompt ? `Content for: ${selectedPrompt.name}` : 'Select a prompt'}
              </h2>
              {isLoadingContent && <p>Loading prompt content...</p>}
              {!selectedPrompt && !isLoadingContent && !error && (
                <p className="text-muted-foreground">Select a prompt from the list to view its content.</p>
              )}
              {selectedPrompt && !isLoadingContent && (
                <div className="prompt-content-area p-4 border rounded-md bg-background shadow-sm min-h-[300px] overflow-auto">
                  <pre className="whitespace-pre-wrap font-mono text-sm">
                    {selectedPrompt.content}
                  </pre>
                </div>
              )}
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default PromptManagementPage;

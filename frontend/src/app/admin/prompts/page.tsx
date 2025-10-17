'use client';

import { useState, useEffect } from 'react';
import { fetchApi } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from '@/components/ui/card';
import { Textarea } from '@/components/ui/textarea';
import { Skeleton } from '@/components/ui/skeleton';
import { toast } from "sonner";
import { PromptFile } from '@/types/PromptFile';
import { PromptContent } from '@/types/PromptContent';

function PromptListSkeleton() {
  return (
    <div className="space-y-2">
      {[...Array(6)].map((_, i) => (
        <Skeleton key={i} className="h-9 w-full" />
      ))}
    </div>
  );
}

export default function PromptsPage() {
  const [prompts, setPrompts] = useState<PromptFile[]>([]);
  const [selectedPrompt, setSelectedPrompt] = useState<PromptFile | null>(null);
  const [promptContent, setPromptContent] = useState<string>('');
  const [isLoadingList, setIsLoadingList] = useState<boolean>(true);
  const [isLoadingContent, setIsLoadingContent] = useState<boolean>(false);
  const [isSaving, setIsSaving] = useState<boolean>(false);

  useEffect(() => {
    const fetchPrompts = async () => {
      setIsLoadingList(true);
      try {
        const response = await fetchApi('/api/prompts');
        if (!response.ok) throw new Error('Failed to fetch prompts');
        const data: { prompts: PromptFile[] } = await response.json();
        setPrompts(data.prompts);
      } catch (e) {
        const errorMessage = e instanceof Error ? e.message : String(e);
        toast.error(`Failed to load prompts: ${errorMessage}`);
      } finally {
        setIsLoadingList(false);
      }
    };
    fetchPrompts();
  }, []);

  const handlePromptSelect = async (prompt: PromptFile) => {
    setSelectedPrompt(prompt);
    setIsLoadingContent(true);
    try {
      const response = await fetchApi(`/api/prompts/${prompt.path}`);
      if (!response.ok) throw new Error('Failed to fetch prompt content');
      const data: PromptContent = await response.json();
      setPromptContent(data.content);
    } catch (e) {
      const errorMessage = e instanceof Error ? e.message : String(e);
      toast.error(`Failed to load prompt content: ${errorMessage}`);
      setPromptContent('');
    } finally {
      setIsLoadingContent(false);
    }
  };

  const handleSave = async () => {
    if (!selectedPrompt) return;

    setIsSaving(true);
    try {
      const response = await fetchApi(`/api/prompts/${selectedPrompt.path}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: promptContent }),
      });
      if (!response.ok) throw new Error('Failed to save prompt');
      toast.success(`Prompt "${selectedPrompt.filename}" saved successfully.`);
    } catch (e) {
      const errorMessage = e instanceof Error ? e.message : String(e);
      toast.error(`Failed to save prompt: ${errorMessage}`);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
      <Card className="md:col-span-1">
        <CardHeader>
          <CardTitle>Prompts</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoadingList ? (
            <PromptListSkeleton />
          ) : (
            <div className="space-y-2">
              {prompts.map((prompt) => (
                <Button
                  key={prompt.path}
                  variant={selectedPrompt?.path === prompt.path ? 'secondary' : 'ghost'}
                  className="w-full justify-start"
                  onClick={() => handlePromptSelect(prompt)}
                >
                  {prompt.filename}
                </Button>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Card className="md:col-span-2">
        <CardHeader>
          <CardTitle>{selectedPrompt ? `Editing: ${selectedPrompt.filename}` : 'Select a prompt'}</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoadingContent ? (
            <Skeleton className="h-96 w-full" />
          ) : selectedPrompt ? (
            <Textarea
              value={promptContent}
              onChange={(e) => setPromptContent(e.target.value)}
              className="h-96 font-mono"
              placeholder="Prompt content..."
            />
          ) : (
            <div className="flex items-center justify-center h-96 text-muted-foreground">
              <p>Select a prompt from the list to view and edit its content.</p>
            </div>
          )}
        </CardContent>
        {selectedPrompt && (
          <CardFooter>
            <Button onClick={handleSave} disabled={isSaving || isLoadingContent}>
              {isSaving ? 'Saving...' : 'Save Changes'}
            </Button>
          </CardFooter>
        )}
      </Card>
    </div>
  );
}

'use client';

import { useState, useEffect, ChangeEvent } from 'react';
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
        const response = await fetch('/api/prompts');
        if (!response.ok) throw new Error('Failed to fetch prompts');
        const data: { prompts: PromptFile[] } = await response.json();
        setPrompts(data.prompts);
      } catch (e: any) {
        toast.error(`Failed to load prompts: ${e.message}`);
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
      const response = await fetch(`/api/prompts/${prompt.name}`);
      if (!response.ok) throw new Error('Failed to fetch prompt content');
      const data: PromptContent = await response.json();
      setPromptContent(data.content);
    } catch (e: any) {
      toast.error(`Failed to load prompt content: ${e.message}`);
      setPromptContent('');
    } finally {
      setIsLoadingContent(false);
    }
  };

  const handleSave = async () => {
    if (!selectedPrompt) return;

    setIsSaving(true);
    try {
      const response = await fetch(`/api/prompts/${selectedPrompt.name}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: promptContent }),
      });
      if (!response.ok) throw new Error('Failed to save prompt');
      toast.success(`Prompt "${selectedPrompt.name}" saved successfully.`);
    } catch (e: any) {
      toast.error(`Failed to save prompt: ${e.message}`);
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
                  key={prompt.name}
                  variant={selectedPrompt?.name === prompt.name ? 'secondary' : 'ghost'}
                  className="w-full justify-start"
                  onClick={() => handlePromptSelect(prompt)}
                >
                  {prompt.name}
                </Button>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Card className="md:col-span-2">
        <CardHeader>
          <CardTitle>{selectedPrompt ? `Editing: ${selectedPrompt.name}` : 'Select a prompt'}</CardTitle>
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

import Link from "next/link";
import { Button } from "@/components/ui/button";

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-between p-24">
      <div className="z-10 max-w-5xl w-full items-center justify-between font-mono text-sm lg:flex">
        <h1 className="text-4xl font-bold text-center mb-8">MCP Admin</h1>
        <p className="text-center mb-8">
          Management interface for MCP operations
        </p>

        <div className="grid grid-cols-2 md:grid-cols-3 gap-4 w-full max-w-2xl">
          <Link href="/products">
            <Button className="w-full h-20 flex flex-col items-center justify-center">
              <h3 className="font-semibold mb-2">Products</h3>
              <p className="text-sm text-muted-foreground">Manage product data</p>
            </Button>
          </Link>

          <Link href="/models">
            <Button className="w-full h-20 flex flex-col items-center justify-center">
              <h3 className="font-semibold mb-2">Models</h3>
              <p className="text-sm text-muted-foreground">AI model management</p>
            </Button>
          </Link>

          <Link href="/pipelines">
            <Button className="w-full h-20 flex flex-col items-center justify-center">
              <h3 className="font-semibold mb-2">Pipelines</h3>
              <p className="text-sm text-muted-foreground">Pipeline operations</p>
            </Button>
          </Link>

          <Link href="/database">
            <Button className="w-full h-20 flex flex-col items-center justify-center">
              <h3 className="font-semibold mb-2">Database</h3>
              <p className="text-sm text-muted-foreground">Database management</p>
            </Button>
          </Link>

          <Link href="/changes">
            <Button className="w-full h-20 flex flex-col items-center justify-center">
              <h3 className="font-semibold mb-2">Changes</h3>
              <p className="text-sm text-muted-foreground">Change log</p>
            </Button>
          </Link>

          <Link href="/prompts">
            <Button className="w-full h-20 flex flex-col items-center justify-center">
              <h3 className="font-semibold mb-2">Prompts</h3>
              <p className="text-sm text-muted-foreground">Prompt management</p>
            </Button>
          </Link>
        </div>
      </div>
    </main>
  );
}

import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { DarkModeToggle } from "@/components/gallery/DarkModeToggle";
import { PROJECT_NAME, PROJECT_DESCRIPTION } from "./config";

// When VITE_API_BASE_URL is set (e.g. in CI preview builds), target FastAPI at
// that absolute origin (cross-origin). Falls back to the relative /api dev-proxy
// path when unset (existing Vite dev-server behavior, unchanged).
const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "/api";

export default function App() {
  const [isFetching, setIsFetching] = useState(false);

  async function handleTraceFetch(traceTestId?: string) {
    setIsFetching(true);
    try {
      const url = traceTestId
        ? `${API_BASE}/trace-demo?trace_test_id=${encodeURIComponent(traceTestId)}`
        : `${API_BASE}/trace-demo`;
      const res = await fetch(url);
      toast(`Fetch returned ${res.status}. Check \`just trace --last\` for the waterfall.`);
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      toast.error(`Fetch failed: ${message}. Is the backend running?`);
    } finally {
      setIsFetching(false);
    }
  }

  return (
    <main className="min-h-screen bg-background text-foreground">
      <header className="sticky top-0 z-10 border-b bg-background p-8">
        <div className="flex items-start justify-between gap-4">
          <div className="space-y-1">
            <h1 className="text-4xl font-bold tracking-tight">{PROJECT_NAME} — Component Gallery</h1>
            <p className="text-sm text-muted-foreground">{PROJECT_DESCRIPTION}</p>
            <p className="text-sm text-muted-foreground">
              Component gallery. Replace App.tsx with your real app.
            </p>
          </div>
          <DarkModeToggle />
        </div>
      </header>

      <div className="container mx-auto space-y-12 px-8 py-12">
        {/* Trace test affordance */}
        <section className="p-6 border-b">
          <h2 className="text-2xl font-semibold">Trace test</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Fires a fetch to /api/trace-demo and shows OTel propagation in a toast.
          </p>
          <div className="mt-4">
            <Button
              onClick={() => handleTraceFetch()}
              disabled={isFetching}
              aria-busy={isFetching}
            >
              Fire test fetch
            </Button>
          </div>
        </section>

        {/* Button gallery */}
        <section
          id="gallery-button"
          data-lost-pixel-id="gallery-button"
          className="p-6 border-b"
        >
          <h2 className="text-2xl font-semibold">Button</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Primary, secondary, destructive, outline, ghost, link.
          </p>
          <div className="mt-4 flex flex-wrap gap-4">
            <Button variant="default">Default</Button>
            <Button variant="secondary">Secondary</Button>
            <Button variant="destructive">Destructive</Button>
            <Button variant="outline">Outline</Button>
            <Button variant="ghost">Ghost</Button>
            <Button variant="link">Link</Button>
            <Button disabled>Disabled</Button>
            <Button aria-busy="true">
              <span className="animate-spin mr-2">&#9696;</span>Loading
            </Button>
          </div>
        </section>

        {/* Card gallery */}
        <section
          id="gallery-card"
          data-lost-pixel-id="gallery-card"
          className="p-6 border-b"
        >
          <h2 className="text-2xl font-semibold">Card</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Container with header, content, footer slots.
          </p>
          <div className="mt-4 max-w-sm">
            <Card>
              <CardHeader>
                <CardTitle>Card title</CardTitle>
                <CardDescription>Card description</CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-sm">Card content goes here.</p>
              </CardContent>
              <CardFooter>
                <Button size="sm">Action</Button>
              </CardFooter>
            </Card>
          </div>
        </section>

        {/* Input gallery */}
        <section
          id="gallery-input"
          data-lost-pixel-id="gallery-input"
          className="p-6 border-b"
        >
          <h2 className="text-2xl font-semibold">Input</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Form input. Paired with a Label for accessibility.
          </p>
          <div className="mt-4 flex flex-col gap-4 max-w-sm">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="input-default">Default input</Label>
              <Input id="input-default" placeholder="Type here" />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="input-disabled">Disabled input</Label>
              <Input id="input-disabled" placeholder="Type here" disabled />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="input-invalid">Invalid input</Label>
              <Input
                id="input-invalid"
                placeholder="Type here"
                aria-invalid="true"
                aria-describedby="input-invalid-error"
              />
              <span
                id="input-invalid-error"
                className="text-sm text-destructive"
              >
                This field is required.
              </span>
            </div>
          </div>
        </section>

        {/* Label gallery */}
        <section
          id="gallery-label"
          data-lost-pixel-id="gallery-label"
          className="p-6 border-b"
        >
          <h2 className="text-2xl font-semibold">Label</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Accessible label primitive. Use htmlFor to associate with inputs.
          </p>
          <div className="mt-4 flex flex-col gap-2">
            <Label>Standalone label</Label>
            <Label className="text-muted-foreground">Muted label</Label>
          </div>
        </section>

        {/* Dialog gallery */}
        {/*
          Dialog renders with defaultOpen so the Lost Pixel snapshot in plan 07-06
          captures the portal-rendered dialog content (Radix portal verification).
          This verifies that Tailwind v4 CSS cascade survives the portal boundary.

          modal={false}: a modal Dialog sets aria-hidden on all sibling content,
          which hides the rest of the gallery (including the DarkModeToggle) from
          the accessibility tree and traps focus — breaking the role-based E2E and
          axe interactions in plans 07-05/07-06. Non-modal keeps the portal content
          visible for snapshots without aria-hiding or locking the page.
        */}
        <section
          id="gallery-dialog"
          data-lost-pixel-id="gallery-dialog"
          className="p-6 border-b"
        >
          <h2 className="text-2xl font-semibold">Dialog</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Modal overlay. Esc or backdrop click to close.
          </p>
          <div className="mt-4">
            <Dialog defaultOpen modal={false}>
              <DialogTrigger asChild>
                <Button variant="outline">Open</Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Example dialog</DialogTitle>
                  <DialogDescription>
                    Replace this with real content.
                  </DialogDescription>
                </DialogHeader>
                <DialogFooter>
                  <Button variant="outline">Cancel</Button>
                  <Button>Confirm</Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>
        </section>

        {/* Sheet gallery */}
        {/*
          Sheet renders with defaultOpen so the Lost Pixel snapshot in plan 07-06
          captures the portal-rendered sheet content (side-drawer portal verification).
          This verifies that Tailwind v4 CSS cascade survives the portal boundary.

          modal={false}: see the Dialog note above — a modal Sheet aria-hides and
          focus-traps the rest of the page, breaking the toggle E2E/axe interactions.
        */}
        <section
          id="gallery-sheet"
          data-lost-pixel-id="gallery-sheet"
          className="p-6 border-b"
        >
          <h2 className="text-2xl font-semibold">Sheet</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Side drawer. Same interaction as Dialog.
          </p>
          <div className="mt-4">
            <Sheet defaultOpen modal={false}>
              <SheetTrigger asChild>
                <Button variant="outline">Open</Button>
              </SheetTrigger>
              <SheetContent>
                <SheetHeader>
                  <SheetTitle>Example sheet</SheetTitle>
                  <SheetDescription>
                    Replace this with real content.
                  </SheetDescription>
                </SheetHeader>
              </SheetContent>
            </Sheet>
          </div>
        </section>

        {/* Toast gallery */}
        <section
          id="gallery-toast"
          data-lost-pixel-id="gallery-toast"
          className="p-6 border-b"
        >
          <h2 className="text-2xl font-semibold">Toast</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Transient notification. Auto-dismisses.
          </p>
          <div className="mt-4">
            <Button
              variant="outline"
              onClick={() => toast("Toast fired. Auto-dismisses in a moment.")}
            >
              Show toast
            </Button>
          </div>
        </section>
      </div>

      <footer className="border-t p-8">
        <p className="text-sm text-muted-foreground">
          Generated by verify-kit. Run{" "}
          <code className="font-mono">`just verify --web`</code> to validate.
        </p>
      </footer>
    </main>
  );
}

# ADR 0004: Frontend Framework Choice

## Status
Accepted

## Context
The project requires a user interface for querying the knowledge copilot. The interface needs to display natural language responses, citation links, and potentially system traces or reasoning steps.

## Decision
We will use **React / Next.js** (App Router) as the primary frontend framework, styled with **shadcn/ui** and Tailwind CSS.

## Rationale
- **Web-First Priority:** Next.js provides the best-in-class developer experience for building high-performance, SEO-friendly web applications, which aligns with standard enterprise desktop usage.
- **UI Consistency & Premium Aesthetics:** Combining Next.js with `shadcn/ui` allows us to rapidly build a premium, highly customized interface with modern dynamic aesthetics (micro-animations, accessible components).
- **Streaming Support:** React and Next.js make it very straightforward to implement SSE (Server-Sent Events) hooks to support Optimistic Streaming (the "Revoke" Method) for the LLM responses.
- **Development Speed:** High-quality React components and robust tooling support rapid prototyping of the chat interface and citation views.

## Alternatives Considered
- **Flutter:** Originally chosen for cross-platform capabilities, but discarded in favor of Next.js to achieve a more modern, premium web-native aesthetic with less overhead for web deployment.

## Consequences
- Requires Node.js and npm environment setup for frontend developers.
- Integration with FastAPI will be handled via standard REST and SSE protocols.

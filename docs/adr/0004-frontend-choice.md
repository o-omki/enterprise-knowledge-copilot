# ADR 0004: Frontend Framework Choice

## Status
Accepted

## Context
The project requires a user interface for querying the knowledge copilot. The interface needs to display natural language responses, citation links, and potentially system traces or reasoning steps.

## Decision
We will use **Flutter** as the primary frontend framework.

## Rationale
- **Cross-Platform:** Flutter allows for a single codebase to target Web, Desktop (Windows/Linux/macOS), and Mobile, which aligns with future enterprise scalability goals.
- **UI Consistency:** Flutter's custom rendering engine ensures pixel-perfect consistency across all target platforms.
- **Development Speed:** High-quality widgets and "hot reload" support rapid prototyping of the chat interface and citation views.
- **User Preference:** Explicitly requested by the user.

## Alternatives Considered
- **React / Next.js:** Strong ecosystem for web, but requires additional effort (React Native) for a high-quality native mobile/desktop experience.

## Consequences
- Requires Flutter SDK and Dart environment setup for frontend developers.
- Integration with FastAPI will be handled via standard REST/WebSocket protocols.

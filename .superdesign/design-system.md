# Residencia Fiscal design system

Residencia Fiscal is a research interface for Spanish tax-residence jurisprudence. The user must perceive documentary rigor, clarity and verifiability.

## Visual direction

- Preserve the existing sober legal-document aesthetic.
- Use borders before shadows. Shadows remain neutral and subtle.
- Use only tokens from `frontend/src/index.css`.
- Do not use gradients, colored shadows, scales on hover, balance scales, gavels, flags, classical columns, robots, mascots or 3D illustrations.
- Space Grotesk is reserved for headings; Inter is the interface font.
- Primary slate blue communicates structure and action. Amber is earned by citations and important notices, not decoration.
- Rounded corners are restrained: 0.5rem base, rounded-xl for controls.
- Focus is always the shared `control-focus` ring.
- The chat has one primary action: submit the query.

## Composer-specific behavior

- The composer remains anchored at the bottom of the chat above the common footer.
- It must be visually discoverable on first visit and after reading a long response.
- It grows from one row to a maximum of 160px.
- Send remains a 40×40 primary icon control; stop remains an outline icon control.
- The highlight must not imply an error or warning and must preserve accessible contrast.
- Prefer a stronger primary-tinted border/surface hierarchy over decorative animation.
- The placeholder remains `Escribe tu consulta sobre residencia fiscal…`.

## Tokens

Use the compact source-of-truth summary in `.superdesign/init/theme.md` and the full tokens in `frontend/src/index.css`.

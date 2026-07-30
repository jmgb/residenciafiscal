# Key pages and dependency trees

## /espana — jurisprudence chat

Entry: `frontend/src/pages/SpainPage.tsx`

- frontend/src/pages/SpainPage.tsx
  - frontend/src/components/chat/ChatView.tsx
    - frontend/src/components/chat/ChatComposer.tsx
      - frontend/src/shared/components/ui/button.tsx
      - frontend/src/shared/lib/utils.ts
    - frontend/src/components/chat/ChatWelcome.tsx
    - frontend/src/components/chat/ChatBubble.tsx
      - frontend/src/components/chat/ChatMessageContent.tsx
        - frontend/src/components/chat/ChatSources.tsx
        - frontend/src/components/normativa/NormativaAplicada.tsx
    - frontend/src/stores/useConversations.ts
    - frontend/src/types/chat.ts
  - frontend/src/lib/chat-engine.ts
  - frontend/src/data/countryRoutes.ts
- frontend/src/components/layout/AppLayout.tsx
  - frontend/src/components/layout/AppSidebar.tsx
  - frontend/src/components/layout/MobileNavigation.tsx
  - frontend/src/components/layout/SiteFooter.tsx
  - frontend/src/components/layout/SidebarContent.tsx
  - frontend/src/shared/components/ui/button.tsx
  - frontend/src/shared/components/ui/sheet.tsx

## Country landing pages

Entry: `frontend/src/pages/CountryPage.tsx`

- frontend/src/pages/CountryPage.tsx
  - frontend/src/data/countryRoutes.ts
  - frontend/src/lib/contribution.ts
- frontend/src/components/layout/AppLayout.tsx and its layout dependencies above

## /manifiesto

Entry: `frontend/src/pages/ManifiestoPage.tsx`

- frontend/src/pages/ManifiestoPage.tsx
  - frontend/src/data/staticRoutes.ts
  - frontend/src/lib/usePageTitle.ts
- frontend/src/components/layout/AppLayout.tsx and its layout dependencies above

## /metodologia

Entry: `frontend/src/pages/MetodologiaPage.tsx`

- frontend/src/pages/MetodologiaPage.tsx
  - frontend/src/data/staticRoutes.ts
  - frontend/src/lib/usePageTitle.ts
- frontend/src/components/layout/AppLayout.tsx and its layout dependencies above

## /colaborar

Entry: `frontend/src/pages/ColaborarPage.tsx`

- frontend/src/pages/ColaborarPage.tsx
  - frontend/src/data/countryRoutes.ts
  - frontend/src/data/staticRoutes.ts
  - frontend/src/lib/contribution.ts
  - frontend/src/lib/usePageTitle.ts
- frontend/src/components/layout/AppLayout.tsx and its layout dependencies above

# Extractable components

## AppLayout
- Source: `frontend/src/components/layout/AppLayout.tsx`
- Category: layout
- Description: Full-height desktop/mobile shell with sidebar, sticky page title bar, content outlet and footer.
- Extractable props: selectedCountry (string), sidebarCollapsed (boolean)
- Hardcoded: structure, icons, typography, CSS classes and footer placement

## SidebarContent
- Source: `frontend/src/components/layout/SidebarContent.tsx`
- Category: layout
- Description: Brand, navigation, country list and conversation history shared by desktop and mobile navigation.
- Extractable props: collapsed (boolean), activeCountry (string)
- Hardcoded: logo, labels, icon names and CSS classes

## SiteFooter
- Source: `frontend/src/components/layout/SiteFooter.tsx`
- Category: layout
- Description: Compact legal/product footer below the main application area.
- Extractable props: none
- Hardcoded: copy, links and CSS classes

## ChatComposer
- Source: `frontend/src/components/chat/ChatComposer.tsx`
- Category: basic
- Description: Auto-growing chat textarea with send/stop action and character limit.
- Extractable props: placeholder (string), isStreaming (boolean)
- Hardcoded: send/stop icons, labels, maximum height and CSS classes

## Button
- Source: `frontend/src/shared/components/ui/button.tsx`
- Category: basic
- Description: Shared CVA button with semantic variants and sizes.
- Extractable props: variant (string), size (string), disabled (boolean)
- Hardcoded: variant CSS and interaction states

## Sheet
- Source: `frontend/src/shared/components/ui/sheet.tsx`
- Category: basic
- Description: Radix dialog-based mobile side sheet.
- Extractable props: side (string), open (boolean)
- Hardcoded: overlay, close icon and transition classes

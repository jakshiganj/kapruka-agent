---
name: Luminous Commerce Concierge
colors:
  surface: '#fcf9f8'
  surface-dim: '#dcd9d9'
  surface-bright: '#fcf9f8'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f6f3f2'
  surface-container: '#f0eded'
  surface-container-high: '#eae7e7'
  surface-container-highest: '#e5e2e1'
  on-surface: '#1b1c1c'
  on-surface-variant: '#494550'
  inverse-surface: '#303030'
  inverse-on-surface: '#f3f0ef'
  outline: '#7a7581'
  outline-variant: '#cbc4d1'
  surface-tint: '#68519a'
  primary: '#2a1059'
  on-primary: '#ffffff'
  primary-container: '#402970'
  on-primary-container: '#ac94e2'
  inverse-primary: '#d1bcff'
  secondary: '#6f5d00'
  on-secondary: '#ffffff'
  secondary-container: '#fdd818'
  on-secondary-container: '#705e00'
  tertiary: '#321e00'
  on-tertiary: '#ffffff'
  tertiary-container: '#4e3100'
  on-tertiary-container: '#c4995f'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#eaddff'
  primary-fixed-dim: '#d1bcff'
  on-primary-fixed: '#230653'
  on-primary-fixed-variant: '#503981'
  secondary-fixed: '#ffe166'
  secondary-fixed-dim: '#e7c400'
  on-secondary-fixed: '#221b00'
  on-secondary-fixed-variant: '#544600'
  tertiary-fixed: '#ffddb4'
  tertiary-fixed-dim: '#edbf81'
  on-tertiary-fixed: '#291800'
  on-tertiary-fixed-variant: '#60400e'
  background: '#fcf9f8'
  on-background: '#1b1c1c'
  surface-variant: '#e5e2e1'
  surface-subtle: '#F0EEFA'
  white: '#FFFFFF'
  agent-bubble: '#402970'
  user-bubble: '#F0EEFA'
  accent-yellow: '#FBD614'
typography:
  headline-lg:
    fontFamily: Hanken Grotesk
    fontSize: 24px
    fontWeight: '700'
    lineHeight: 32px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Hanken Grotesk
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
  body-lg:
    fontFamily: Hanken Grotesk
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-md:
    fontFamily: Hanken Grotesk
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  label-lg:
    fontFamily: Hanken Grotesk
    fontSize: 14px
    fontWeight: '600'
    lineHeight: 20px
    letterSpacing: 0.01em
  label-sm:
    fontFamily: Hanken Grotesk
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: 0.03em
  headline-lg-mobile:
    fontFamily: Hanken Grotesk
    fontSize: 20px
    fontWeight: '700'
    lineHeight: 28px
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  base: 8px
  margin-page: 24px
  margin-mobile: 16px
  gutter: 16px
  bubble-padding: 12px 16px
  stack-sm: 4px
  stack-md: 12px
  stack-lg: 24px
---

## Brand & Style
The design system embodies a "Service-First Modernism" aesthetic. It balances the energetic commercial spirit of the brand with a clean, high-fidelity chat experience. The target audience includes both local and international shoppers seeking a reliable, high-touch retail experience.

The visual style is **Corporate Modern with Tactile Accents**. It utilizes high-quality whitespace, crisp structural lines, and a focused color palette to ensure the user feels they are in a secure, professional environment. The emotional response is one of efficiency, warmth, and trust—moving away from cluttered e-commerce layouts toward a streamlined, conversational flow.

## Colors
The palette is rooted in the brand's deep indigo-purple and vibrant yellow. 

- **Primary (#402970):** Used for high-authority elements, agent message bubbles, and primary call-to-action buttons. It provides a sense of depth and luxury.
- **Secondary (#FBD614):** Reserved for highlights, active states, and "attention" markers. It is used sparingly to prevent visual fatigue while maintaining brand recognition.
- **Neutral/Surface:** The background utilizes pure white (#FFFFFF) for clarity, with #F0EEFA serving as a soft alternative for message backgrounds and input containers to differentiate layers without harsh borders.
- **Text:** Primary text is set in #222222 for maximum legibility, while a 60% opacity version is used for timestamps and secondary metadata.

## Typography
This design system moves from the standard Roboto to **Hanken Grotesk** to achieve a more contemporary, sharp, and premium tech-forward feel. 

- **Headlines:** Use Bold and Semi-Bold weights with tight letter-spacing to create a strong visual anchor.
- **Body:** Standardized at 16px for desktop and 14px for mobile to ensure high readability in fast-paced chat environments.
- **Labels:** Used for timestamps, "seen" receipts, and agent names. These use a medium weight and slightly increased letter-spacing for clarity at small sizes.

## Layout & Spacing
The layout follows a **Fixed-Width Center-Aligned** model for desktop chat (max-width 800px) and a **Fluid** model for mobile.

- **Grid:** A standard 8px baseline grid ensures vertical rhythm.
- **Chat Flow:** Message groups are separated by 24px (stack-lg), while individual bubbles within a group from the same sender are separated by 4px (stack-sm).
- **Safe Zones:** A 16px horizontal margin is maintained on mobile to ensure text doesn't touch the screen edges.
- **Input Area:** The message input is pinned to the bottom, floating with a subtle blur or anchored with a clear top-border for structural definition.

## Elevation & Depth
The design system utilizes **Tonal Layering** with occasional **Ambient Shadows** to define hierarchy.

- **Level 0 (Base):** The main background using #FFFFFF.
- **Level 1 (Containers):** The chat input area and sidebars use #F0EEFA with no shadow, defined by a 1px border in a slightly darker tint of the primary color at 10% opacity.
- **Level 2 (Active Elements):** Message bubbles and dropdowns. User bubbles are flat (Level 1), while Agent bubbles utilize a soft, 8% opacity shadow with a 4px blur to appear slightly elevated, signaling their "concierge" status.
- **Level 3 (Pop-overs):** Tooltips and product cards within the chat utilize a more pronounced shadow (12% opacity, 12px blur) to sit clearly above the conversation.

## Shapes
The shape language is **Refined & Modern**. 

- **Standard Bubbles:** Use a 16px radius (rounded-lg). To distinguish sender types, the "tail" corner of the bubble is sharpened to 4px.
- **Buttons & Inputs:** Use a 0.5rem (8px) radius to maintain a professional, sturdy appearance. 
- **Product Cards:** Use 1rem (16px) radius to feel like distinct, touchable objects within the flow.
- **Avatars:** Strictly circular (pill-shaped) to provide a soft, human contrast to the structured chat interface.

## Components
- **Message Bubbles:**
    - *Agent:* Background Primary (#402970), Text White, Left-aligned.
    - *User:* Background Surface-Subtle (#F0EEFA), Text Neutral (#222222), Right-aligned.
- **Buttons:**
    - *Primary:* Background Primary, Text White. High-gloss finish on hover.
    - *Secondary:* Background Secondary (#FBD614), Text Neutral. Used for "Buy Now" or "Checkout" actions within the chat.
- **Input Field:** A full-width container with a subtle inner shadow or light gray border. Icons for "Attach" and "Emoji" are displayed in Primary color at 60% opacity.
- **Product Cards:** Embedded in-chat cards featuring a small image (left), product title, price (in Primary color), and a Secondary-colored "Add to Cart" button.
- **Status Indicators:** Small circular dots for "Online" (Green) and "Busy" (Yellow), placed at the bottom-right of the agent's avatar.
- **Chips:** Used for quick-reply suggestions (e.g., "Where is my order?", "Product Inquiry"). These have a Primary color border and #FFFFFF background.
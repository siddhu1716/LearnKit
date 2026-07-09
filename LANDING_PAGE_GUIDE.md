# LIA LABS Landing Page - Complete Setup Guide

## Project Overview
This is the official LIA LABS landing page showcasing:
- **LIA LABS**: The AI infrastructure company
- **LearnKit**: The open-source Experience Distillation SDK

## What's New

### 🎨 Professional Landing Page
- **Hero Section**: Stunning spiral animation background with tagline "We Make Your Agents Learn, Improve & Adapt"
- **About Section**: Clear positioning of what LIA LABS does
- **Problems We Solve**: Five key problems addressed by our platform
- **LearnKit Spotlight**: Dedicated section for the open-source SDK
- **Features Grid**: Six powerful capabilities
- **Interactive Dashboard Preview**: Tabbed dashboard with multiple views
- **CTA Section**: Strong call-to-action buttons
- **Professional Footer**: Navigation and branding

### 🎯 Key Features
1. **Spiral Animation**: Custom 3D GSAP animation with 5000 particles
2. **Tailwind CSS v4**: Modern utility-first styling
3. **Interactive Components**: Tabbed dashboard preview with real metrics
4. **Professional Typography**: Geist font for clean, modern look
5. **Dark Theme**: Premium emerald and violet accent colors
6. **Fully Responsive**: Mobile-first design

## Architecture

### Directory Structure
```
src/
├── components/
│   ├── ui/
│   │   └── spiral-animation.tsx    # 3D spiral animation
│   └── landing/
│       └── DashboardPreview.tsx    # Interactive dashboard
├── pages/
│   └── landing/
│       └── LandingPage.tsx         # Main landing page
├── styles/
│   └── landing.css                 # Tailwind imports
└── landing-main.tsx                # Entry point

index.html                           # Landing page entry
```

### Component Breakdown

#### SpiralAnimation
- Pure TypeScript 3D graphics
- Uses Canvas API with GSAP
- 5000 animated particles in spiral formation
- Auto-responsive to window resize
- Colors: Emerald (#00ff88) on black background

#### DashboardPreview
- Four interactive tabs: Overview, Memory, Performance, Tasks
- Mock metrics and data visualization
- Progress bars and status indicators
- Responsive grid layout
- Uses Lucide icons

#### LandingPage
- Main page component
- Sections: Hero, About, Problems, LearnKit, Features, Dashboard, CTA, Footer
- Smooth scroll animation
- Section scroll detection for reveal effects

## Technology Stack
- **React 18**: UI framework
- **TypeScript**: Type safety
- **Tailwind CSS v4**: Utility styling with new @import syntax
- **GSAP 3**: Professional animations
- **Vite 5**: Build tool with HMR
- **Lucide React**: Icon library

## Development

### Installation
```bash
cd Docs/dashboard
npm install
```

### Development Server
```bash
npm run dev
# Opens on http://localhost:5174
```

### Production Build
```bash
npm run build
# Output in dist/
```

## Customization Guide

### Colors
Edit `tailwind.config.ts`:
```typescript
colors: {
  accent: '#00ff88',      // Main accent (emerald)
  secondary: '#a78bfa',   // Secondary accent (violet)
}
```

### Fonts
Currently using Geist (loaded from Google Fonts)
- Font family configured in `tailwind.config.ts`
- Can swap for different Google Font

### Sections
Edit `src/pages/landing/LandingPage.tsx`:
- Add new sections by duplicating section structure
- Use consistent spacing: `py-24 px-6`
- Wrap in `<section id="section-name">` for scroll links

### Dashboard Tabs
Edit `src/components/landing/DashboardPreview.tsx`:
- Add new tab to `tabs` array
- Add case in `renderContent()` switch statement
- Use consistent card styling

## Integration with Backend

### API Endpoints
The dev server proxies to `http://127.0.0.1:8090` (FastAPI backend):
- `/api/*` → backend API calls
- `/healthz` → health check

Configure in `vite.config.ts`:
```typescript
proxy: {
  '/api': {
    target: 'http://127.0.0.1:8090',
  },
}
```

### Building with Backend
```bash
# Terminal 1: Backend (Python)
cd Docs
python server.py

# Terminal 2: Frontend (Node)
cd Docs/dashboard
npm run dev
```

Both will be accessible at localhost:
- Frontend: `http://localhost:5174`
- Backend API: `http://localhost:8090`

## Performance Optimization

### Bundle Analysis
Current sizes (production):
- CSS: ~32.8 kB (gzipped: 5.6 kB)
- JS (main): ~95.7 kB (gzipped: 35 kB)
- Total: Well under budget

### Tips
- Spiral animation uses requestAnimationFrame for smooth 60fps
- Canvas size scales automatically to device pixel ratio
- Lazy load features grid images if needed
- Consider code-splitting dashboard tab content

## Browser Support
- Chrome/Edge: Latest 2 versions ✓
- Firefox: Latest 2 versions ✓
- Safari: Latest 2 versions ✓
- Mobile browsers: iOS Safari, Chrome Android ✓

## Troubleshooting

### Dev Server Not Starting
- Check if port 5173/5174 is in use
- Clear node_modules and npm install again
- Restart the dev server

### Animations Not Smooth
- Check browser hardware acceleration (DevTools)
- Reduce particles in spiral if needed (edit constant `numberOfStars`)
- Update GPU drivers

### Styling Not Applying
- Ensure `@import "tailwindcss"` is in CSS files
- Rebuild with `npm run build` after CSS changes
- Clear browser cache with Ctrl+F5

## Next Steps

1. **Add More Dashboard Screenshots**: Create image components for each tab
2. **Integrate with Real Backend**: Connect to actual API endpoints
3. **Add Blog Section**: Link to LearnKit documentation
4. **Multi-language Support**: i18n for global audience
5. **Analytics Integration**: Track user engagement
6. **Email Newsletter**: Signup form in CTA section
7. **GitHub Integration**: Show recent commits/releases

## Deployment

### Vercel
```bash
npm install -g vercel
vercel
```

### Netlify
```bash
npm install -g netlify-cli
netlify deploy --prod --dir=dist
```

### Self-hosted
```bash
npm run build
# Serve dist/ folder with any web server
python -m http.server --directory dist 8000
```

## Support & Questions
For issues or feature requests, open an issue on GitHub or contact the LIA LABS team.

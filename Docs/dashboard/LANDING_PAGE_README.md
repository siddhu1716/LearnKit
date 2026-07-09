# LIA LABS - Professional Landing Page

> A stunning, modern landing page for LIA LABS built with React, TypeScript, Tailwind CSS v4, and GSAP animations.

## 🎯 Features

✨ **Spiral Animation Hero**
- Mesmerizing 3D particle animation background
- 5000+ animated emerald particles
- Responsive canvas rendering with device pixel ratio support
- Built with GSAP and Canvas API

🎨 **Modern Design**
- Dark theme with emerald (#00ff88) and violet (#a78bfa) accents
- Professional typography using Geist font
- Fully responsive mobile-first design
- Smooth section transitions and scroll animations

📊 **Interactive Dashboard Preview**
- Tabbed interface with 4 views: Overview, Memory, Performance, Tasks
- Mock metrics and real-time-looking data
- Interactive charts and progress indicators
- Professional card-based layout

⚡ **Performance**
- Vite for fast HMR during development
- Optimized production builds
- CSS ~32kB gzipped, JS ~35kB gzipped
- Canvas animation runs at 60 FPS

## 🚀 Quick Start

### Installation
```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

### Development Server
The dev server runs on `http://localhost:5174` and includes:
- Hot Module Replacement (HMR) for instant updates
- API proxy to `http://127.0.0.1:8090` for backend calls
- Source maps for debugging

## 📁 Project Structure

```
src/
├── components/
│   ├── ui/
│   │   └── spiral-animation.tsx      # 3D spiral animation component
│   └── landing/
│       └── DashboardPreview.tsx      # Interactive dashboard preview
├── pages/
│   └── landing/
│       └── LandingPage.tsx           # Main landing page component
├── styles/
│   └── landing.css                   # Tailwind CSS imports
└── landing-main.tsx                  # Application entry point

tailwind.config.ts                    # Tailwind configuration
postcss.config.js                     # PostCSS configuration
vite.config.ts                        # Vite configuration
index.html                            # Landing page HTML
```

## 🎨 Customization

### Colors
Edit `tailwind.config.ts`:
```typescript
colors: {
  accent: '#00ff88',        // Emerald green
  secondary: '#a78bfa',     // Violet
  // ... other colors
}
```

### Fonts
Change in `tailwind.config.ts`:
```typescript
fontFamily: {
  sans: ['Your Font', ...defaultTheme.fontFamily.sans],
  mono: ['Your Mono Font', ...defaultTheme.fontFamily.mono],
}
```

### Sections
Edit `src/pages/landing/LandingPage.tsx`:
- Each `<section>` represents a major page section
- Use consistent spacing: `py-24 px-6`
- Follow the existing pattern for styling

### Dashboard Tabs
Edit `src/components/landing/DashboardPreview.tsx`:
- Add tabs to the `tabs` array
- Implement content in the `renderContent()` switch statement
- Use consistent card and metric styling

## 🔧 Configuration

### Tailwind CSS v4
Uses new `@import "tailwindcss"` syntax instead of `@tailwind` directives.
Edit `src/styles/landing.css` for custom styles.

### PostCSS
PostCSS configuration includes Tailwind and autoprefixer.
Uses `@tailwindcss/postcss` package for v4 support.

### Vite
Multi-page app setup in `vite.config.ts`:
- `index.html` → landing page
- `app.html` → dashboard (if used)
- `docs.html` → documentation (if used)

## 📊 Dashboard Preview Component

The `DashboardPreview` component features:
- **Overview Tab**: Metrics cards with trends, agent learning curves
- **Memory Tab**: Memory statistics, retrieval quality, recent entries
- **Performance Tab**: Latency distribution, throughput metrics
- **Tasks Tab**: Recent task list with status indicators

All data is currently mocked. To integrate real data:
1. Create API hooks to fetch data
2. Pass data as props to component
3. Update state management as needed

## 🌐 API Integration

The dev server proxies requests to the backend:
```typescript
// In vite.config.ts
'/api': {
  target: 'http://127.0.0.1:8090',
  changeOrigin: true,
}
```

To make API calls:
```typescript
const response = await fetch('/api/endpoint');
const data = await response.json();
```

## 📦 Build & Deploy

### Production Build
```bash
npm run build
# Creates optimized files in dist/
```

### Deployment Options

**Vercel** (Recommended)
```bash
npm install -g vercel
vercel
```

**Netlify**
```bash
npm install -g netlify-cli
netlify deploy --prod --dir=dist
```

**Self-hosted**
```bash
# Using Python
python -m http.server --directory dist 8000

# Using Node.js http-server
npx http-server dist
```

## 🎬 Animation Details

### Spiral Animation
- Uses GSAP timeline for 15-second loop animation
- 5000 particles following spiral paths with easing
- Elastic and power easing functions for natural motion
- 3D perspective with z-depth calculations
- Responsive to window resize events

### Page Transitions
- Fade-in-up animation for sections on scroll
- 0.8s duration with cubic-bezier easing
- Staggered with different delays per element

## 🐛 Troubleshooting

### Dev Server Issues
```bash
# Clear node_modules and reinstall
rm -rf node_modules package-lock.json
npm install
npm run dev
```

### Build Errors
```bash
# Type errors: Run TypeScript compiler
npm run tsc

# CSS errors: Check Tailwind config
npm run build
```

### Animation Not Smooth
- Check browser DevTools Performance tab
- Verify GPU acceleration is enabled
- Reduce particle count if needed (in spiral-animation.tsx)

## 📚 Resources

- [Tailwind CSS Documentation](https://tailwindcss.com)
- [Tailwind CSS v4 Migration](https://tailwindcss.com/docs/upgrade-guide)
- [GSAP Documentation](https://gsap.com)
- [React Documentation](https://react.dev)
- [Vite Documentation](https://vitejs.dev)
- [Lucide Icons](https://lucide.dev)

## 📝 License

This landing page is part of the LIA LABS project. See main repository for license details.

## 🤝 Contributing

Contributions welcome! Please follow the existing code style and component patterns.

## 📞 Support

For issues or questions:
1. Check the troubleshooting section
2. Review the LANDING_PAGE_GUIDE.md for detailed setup
3. Open an issue on GitHub
4. Contact the LIA LABS team

---

**Built with ❤️ for LIA LABS**

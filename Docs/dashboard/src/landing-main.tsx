import React from 'react'
import ReactDOM from 'react-dom/client'
import { LandingPage } from './pages/landing/LandingPage'
import './styles/landing.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <LandingPage />
  </React.StrictMode>
)

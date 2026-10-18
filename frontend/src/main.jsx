import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import 'leaflet/dist/leaflet.css'
import './lib/signal-flow/tokens.css'
import './lib/signal-flow/components.css'
import './lib/signal-flow/signal-flow.js'
import './styles/app.css'
import App from './App.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)

// this file is responsible for defining the main entry point of the application
// It initializes the React application and renders the App component into the root DOM element.
// In simple words,
    // it starts the React app and displays the main App component on the webpage.

import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)

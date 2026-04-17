import React from 'react'
import ReactDOM from 'react-dom/client'
import { ChakraProvider, extendTheme } from '@chakra-ui/react'
import App from './App'

const theme = extendTheme({
  config: {
    initialColorMode: 'dark',
    useSystemColorMode: false,
  },
  fonts: {
    heading: "'Playfair Display', 'Inter', serif",
    body: "'Inter', system-ui, sans-serif",
  },
  styles: {
    global: {
      'html, body': {
        bg: '#0d0e1f',
        color: 'white',
        margin: 0,
        padding: 0,
        scrollBehavior: 'smooth',
      },
      '::selection': {
        bg: '#3b82f640',
        color: 'white',
      },
    },
  },
})

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ChakraProvider theme={theme}>
      <App />
    </ChakraProvider>
  </React.StrictMode>,
)

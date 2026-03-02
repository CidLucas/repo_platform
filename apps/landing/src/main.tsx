import React from 'react'
import ReactDOM from 'react-dom/client'
import { ChakraProvider, extendTheme } from '@chakra-ui/react'
import App from './App'

const theme = extendTheme({
  fonts: {
    heading: "'Noto Sans Thai Looped', 'IBM Plex Sans', sans-serif",
    body: "'IBM Plex Sans', sans-serif",
  },
  styles: {
    global: {
      body: {
        bg: '#9dc5f6',
        margin: 0,
        padding: 0,
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

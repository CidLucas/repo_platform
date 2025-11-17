import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { ChakraProvider, extendTheme } from '@chakra-ui/react'
import { BrowserRouter } from 'react-router-dom'; // Add this import

// Create a theme instance.
const theme = extendTheme({
  fonts: {
    heading: "'Inter', 'Noto Sans Thai Looped', sans-serif",
    body: "'Inter', 'Noto Sans Thai Looped', sans-serif",
  },
  fontWeights: {
    regular: 400,
    medium: 500,
    semibold: 600,
    bold: 700,
  },
  styles: {
    global: {
            body: {
              bg: '#F6F6F6',
              color: 'gray.800',
            },
            // Global style to target the specific class name reported by the user
            '.css-1mgfjbg': {
              background: 'transparent !important',
            },
            // Global style to adjust the position of the Select component's arrow icon
            '.chakra-select__icon-wrapper': {
              right: '5px !important', // Adjusted right position
            },
            // Global style to ensure the Select wrapper provides a positioning context for its dropdown
            '.chakra-select__wrapper': {
              position: 'relative !important',
            },
          },
        },
  textStyles: {
    pageTitle: {
      fontWeight: 400,
      fontSize: "34px",
      lineHeight: "36px",
      letterSpacing: "0.35px",
    },
    pageBigNumber: {
      fontWeight: 600,
      fontSize: "84px",
      lineHeight: "64px",
      letterSpacing: "0.16%",
    },
    pageSubtitle: { // New style
      fontWeight: 400,
      fontSize: "24px",
      lineHeight: "32px",
    },
    pageBigNumberSmall: { // New style
      fontWeight: 600,
      fontSize: "60px",
      lineHeight: "72px",
    },
    homeCardTitle: {
      fontWeight: 500,
      fontSize: "18px",
      lineHeight: "100%",
      letterSpacing: "0%",
      textTransform: "uppercase",
    },
    homeCardPercentage: {
      fontWeight: 600,
      fontSize: "16px",
      lineHeight: "100%",
      letterSpacing: "0%",
    },
    homeCardStatNumber: {
      fontWeight: 600,
      fontSize: "44px",
      lineHeight: "48px",
      letterSpacing: "0.16%",
    },
    homeCardStatLabel: {
      fontWeight: 400,
      fontSize: "12px",
      lineHeight: "20px",
      letterSpacing: "-0.15px",
      textTransform: "uppercase",
    },
    cardHeaderTitle: { // New style
      fontWeight: 500,
      fontSize: "18px",
      lineHeight: "100%",
      letterSpacing: "0%",
      textTransform: "uppercase",
    },
    modalTitle: {
      fontWeight: 500,
      fontSize: "18px",
      lineHeight: "85.4px",
      letterSpacing: "0px",
      textTransform: "uppercase",
    },
    modalTextInfo: {
      fontWeight: 400,
      fontSize: "24px",
      lineHeight: "34px",
      letterSpacing: "0px",
    },
    modalAccordionLabel: {
      fontWeight: 500,
      fontSize: "18px",
      lineHeight: "27px",
      letterSpacing: "-0.44px",
      textTransform: "uppercase",
    },
    modalFinancialInfo: { // New style for financial info list
      fontWeight: 400,
      fontSize: "16px",
      lineHeight: "24px", // Adjusted line height for better readability
      letterSpacing: "0px",
    },
  },
});

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <ChakraProvider theme={theme}>
        <App />
      </ChakraProvider>
    </BrowserRouter>
  </StrictMode>,
)

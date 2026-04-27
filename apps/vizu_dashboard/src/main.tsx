// Dashboard v1.2.0 - Added React Query for data caching
// Initialize Grafana Faro BEFORE React (captures early errors)
import { initFaro } from './lib/faro';
import { initTelemetry } from './lib/telemetry';
initFaro();
initTelemetry();

import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { ChakraProvider, extendTheme } from '@chakra-ui/react'
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from './contexts/AuthContext';
import { TenantProvider } from './contexts/TenantContext';
import { ChatProvider } from './contexts/ChatContext';
import { FaroErrorBoundary } from '@grafana/faro-react';

// Configure React Query with optimal caching settings
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,      // Data considered fresh for 5 minutes
      gcTime: 30 * 60 * 1000,        // Cache kept for 30 minutes (formerly cacheTime)
      refetchOnWindowFocus: false,   // Don't refetch on tab switch
      retry: 2,                       // Retry failed requests twice
    },
  },
});

// Create a theme instance — dark navy theme inspired by Figma Make design
const theme = extendTheme({
  config: {
    initialColorMode: 'dark',
    useSystemColorMode: false,
  },
  fonts: {
    heading: "'Playfair Display', 'Inter', serif",
    body: "'Inter', 'Noto Sans Thai Looped', sans-serif",
  },
  fontWeights: {
    regular: 400,
    medium: 500,
    semibold: 600,
    bold: 700,
  },
  colors: {
    brand: {
      bg: '#0d0e1f',
      card: '#1a1b2e',
      border: 'rgba(255,255,255,0.08)',
      borderHover: 'rgba(255,255,255,0.12)',
      muted: 'rgba(255,255,255,0.6)',
      label: 'rgba(255,255,255,0.5)',
      blue: '#3b82f6',
      purple: '#a855f7',
      pink: '#ec4899',
      green: '#10b981',
      yellow: '#fbbf24',
      orange: '#f97316',
      navyFrom: '#001f3f',
      navyTo: '#003366',
      sidebarFrom: '#001f3f',
      sidebarVia: '#002a54',
      sidebarTo: '#003d7a',
      sidebarActive: '#0ea5e9',
    },
  },
  styles: {
    global: {
      body: {
        bg: '#0d0e1f',
        color: 'white',
      },
      '.css-1mgfjbg': {
        background: 'transparent !important',
      },
      '.chakra-select__icon-wrapper': {
        right: '5px !important',
      },
      '.chakra-select__wrapper': {
        position: 'relative !important',
      },
    },
  },
  components: {
    Card: {
      baseStyle: {
        container: {
          bg: '#1a1b2e',
          borderColor: 'rgba(255,255,255,0.08)',
          borderWidth: '1px',
          borderRadius: '0.625rem',
          boxShadow: '0 4px 24px rgba(0,0,0,0.4)',
          color: 'white',
        },
      },
    },
    Modal: {
      baseStyle: {
        dialog: {
          bg: '#1a1b2e',
          borderColor: 'rgba(255,255,255,0.08)',
          borderWidth: '1px',
          color: 'white',
        },
        header: { color: 'white' },
        body: { color: 'white' },
        closeButton: { color: 'white' },
      },
    },
    Menu: {
      baseStyle: {
        list: {
          bg: '#1a1b2e',
          borderColor: 'rgba(255,255,255,0.08)',
          color: 'white',
        },
        item: {
          bg: 'transparent',
          color: 'white',
          _hover: { bg: 'rgba(255,255,255,0.05)' },
        },
      },
    },
    Input: {
      baseStyle: {
        field: {
          bg: 'rgba(255,255,255,0.05)',
          borderColor: 'rgba(255,255,255,0.08)',
          color: 'white',
          _placeholder: { color: 'rgba(255,255,255,0.4)' },
        },
      },
    },
    Tooltip: {
      baseStyle: {
        bg: '#14151f',
        color: 'white',
        borderRadius: '8px',
      },
    },
  },
  textStyles: {
    pageTitle: {
      fontFamily: "'Playfair Display', serif",
      fontWeight: 400,
      fontSize: "2.5rem",
      lineHeight: "1.2",
      color: "white",
    },
    pageTitleAccent: {
      fontFamily: "'Playfair Display', serif",
      fontWeight: 400,
      fontSize: "2.5rem",
      lineHeight: "1.2",
      bgGradient: "linear(to-r, #ff6b35, #ff006e)",
      bgClip: "text",
    },
    pageSubtitle: {
      fontWeight: 500,
      fontSize: "1.125rem",
      lineHeight: "1.5",
      color: "rgba(255,255,255,0.6)",
    },
    pageBigNumber: {
      fontWeight: 700,
      fontSize: "2.5rem",
      lineHeight: "1",
      color: "white",
    },
    pageBigNumberSmall: {
      fontWeight: 600,
      fontSize: "60px",
      lineHeight: "72px",
    },
    sectionLabel: {
      fontWeight: 600,
      fontSize: "0.75rem",
      lineHeight: "1",
      letterSpacing: "0.05em",
      textTransform: "uppercase",
      color: "rgba(255,255,255,0.5)",
    },
    homeCardTitle: {
      fontWeight: 600,
      fontSize: "0.75rem",
      lineHeight: "1",
      letterSpacing: "0.05em",
      textTransform: "uppercase",
      color: "rgba(255,255,255,0.5)",
    },
    homeCardPercentage: {
      fontWeight: 600,
      fontSize: "16px",
      lineHeight: "100%",
    },
    homeCardStatNumber: {
      fontWeight: 700,
      fontSize: "2.5rem",
      lineHeight: "1",
      color: "white",
    },
    homeCardStatLabel: {
      fontWeight: 400,
      fontSize: "12px",
      lineHeight: "20px",
      letterSpacing: "-0.15px",
      textTransform: "uppercase",
      color: "rgba(255,255,255,0.6)",
    },
    cardHeaderTitle: {
      fontWeight: 500,
      fontSize: "18px",
      lineHeight: "100%",
      letterSpacing: "0%",
      textTransform: "uppercase",
      color: "white",
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
    modalFinancialInfo: {
      fontWeight: 400,
      fontSize: "16px",
      lineHeight: "24px",
      letterSpacing: "0px",
    },
  },
});

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <FaroErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <ChakraProvider theme={theme}>
            <AuthProvider>
              <TenantProvider>
                <ChatProvider>
                  <App />
                </ChatProvider>
              </TenantProvider>
            </AuthProvider>
          </ChakraProvider>
        </BrowserRouter>
      </QueryClientProvider>
    </FaroErrorBoundary>
  </StrictMode>,
)

// API Configuration
// Environment variables are loaded from .env file
export const API_CONFIG = {
  baseUrl: import.meta.env.VITE_AZURE_FUNCTIONS_URL || 'https://cdv-iot-platform-functions.azurewebsites.net',
  functionKey: import.meta.env.VITE_FUNCTION_KEY || '',
  deviceId: import.meta.env.VITE_DEVICE_ID || 'my-new-device-1'
}

// Helper function to build API URL with authentication
export const buildApiUrl = (endpoint: string, params?: Record<string, string>): string => {
  const url = new URL(endpoint, API_CONFIG.baseUrl)

  // Add query parameters
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      url.searchParams.append(key, value)
    })
  }

  // Add function key if available
  if (API_CONFIG.functionKey) {
    url.searchParams.append('code', API_CONFIG.functionKey)
  }

  return url.toString()
}

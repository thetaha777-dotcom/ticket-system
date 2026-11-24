/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Address of the BiletFlow API, without a trailing slash. Default: http://localhost:8000 */
  readonly VITE_API_URL?: string
}

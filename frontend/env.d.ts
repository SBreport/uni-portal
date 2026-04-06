/// <reference types="vite/client" />

import 'vue-router'

declare module 'vue-router' {
  interface RouteMeta {
    public?: boolean
    adminOnly?: boolean
    requiredPermission?: string
    roles?: string[]
  }
}

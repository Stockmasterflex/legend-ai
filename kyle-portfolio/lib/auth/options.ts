import type { NextAuthOptions } from 'next-auth'
import Credentials from 'next-auth/providers/credentials'

const adminEmail = process.env.AUTH_ADMIN_EMAIL
const adminPassword = process.env.AUTH_ADMIN_PASSWORD
const authSecret = process.env.AUTH_SECRET || process.env.NEXTAUTH_SECRET

if (!authSecret) {
  throw new Error('Missing AUTH_SECRET (or NEXTAUTH_SECRET) environment variable. Add it to your env file.')
}

if (!adminEmail || !adminPassword) {
  throw new Error('Missing AUTH_ADMIN_EMAIL or AUTH_ADMIN_PASSWORD environment variables. Add them to your env file.')
}

export const authOptions: NextAuthOptions = {
  secret: authSecret,
  session: {
    strategy: 'jwt',
  },
  pages: {
    signIn: '/login',
  },
  providers: [
    Credentials({
      name: 'Credentials',
      credentials: {
        email: { label: 'Email', type: 'email' },
        password: { label: 'Password', type: 'password' },
      },
      async authorize(credentials) {
        if (!credentials?.email || !credentials?.password) {
          return null
        }
        const email = credentials.email.trim().toLowerCase()
        const password = credentials.password.trim()
        if (email === adminEmail.toLowerCase() && password === adminPassword) {
          return {
            id: 'legend-admin',
            email: adminEmail,
            name: 'Legend Admin',
          }
        }
        return null
      },
    }),
  ],
}

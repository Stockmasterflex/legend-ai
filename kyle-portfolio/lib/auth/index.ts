import NextAuth from 'next-auth'
import { authOptions } from './options'

const handler = NextAuth(authOptions)

export const { auth, signIn, signOut, handlers } = handler
export { authOptions }

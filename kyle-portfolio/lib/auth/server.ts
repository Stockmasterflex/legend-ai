import { getServerSession } from 'next-auth'
import { authOptions } from './options'

export async function auth() {
  return getServerSession(authOptions)
}

import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import {
  onAuthStateChanged,
  signInWithPopup,
  signOut,
  GoogleAuthProvider,
  getIdToken,
} from 'firebase/auth'
import type { User as FirebaseUser } from 'firebase/auth'
import { auth, firebaseEnabled } from '../services/firebase'

interface AuthUser {
  uid: string
  email: string
  displayName: string | null
  photoURL: string | null
  token: string
}

interface AuthContextType {
  user: AuthUser | null
  loading: boolean
  signInWithGoogle: () => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  loading: true,
  signInWithGoogle: async () => {},
  logout: async () => {},
})

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!firebaseEnabled || !auth) {
      setUser(null)
      setLoading(false)
      return
    }

    const unsub = onAuthStateChanged(auth, async (firebaseUser: FirebaseUser | null) => {
      if (firebaseUser) {
        const token = await getIdToken(firebaseUser)
        setUser({
          uid: firebaseUser.uid,
          email: firebaseUser.email ?? '',
          displayName: firebaseUser.displayName,
          photoURL: firebaseUser.photoURL,
          token,
        })
      } else {
        setUser(null)
      }
      setLoading(false)
    })
    return unsub
  }, [])

  const signInWithGoogle = async () => {
    if (!auth) {
      throw new Error('Google sign-in is disabled until Firebase env vars are configured.')
    }

    const provider = new GoogleAuthProvider()
    try {
      await signInWithPopup(auth, provider)
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Google sign-in failed.'
      throw new Error(message)
    }
  }

  const logout = async () => {
    if (!auth) {
      setUser(null)
      return
    }

    await signOut(auth)
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, loading, signInWithGoogle, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)

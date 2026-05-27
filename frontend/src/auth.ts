import NextAuth from "next-auth";
import Google from "next-auth/providers/google";
import Credentials from "next-auth/providers/credentials";
import { SignJWT } from "jose";

type AuthUserFields = {
  id?: string;
  name?: string | null;
  email?: string | null;
  userType?: string;
  accessToken?: unknown;
};

type MutableSession = {
  provider?: unknown;
  user?: AuthUserFields;
};

async function signBackendToken(userId: unknown, email: unknown, secret: Uint8Array) {
  return new SignJWT({ sub: userId as string, email: email as string })
    .setProtectedHeader({ alg: "HS256" })
    .setIssuedAt()
    .setExpirationTime("24h")
    .sign(secret);
}

function isBackendTokenExpired(token: unknown) {
  if (typeof token !== "string") return true;

  try {
    const [, payload] = token.split(".");
    if (!payload) return true;

    const normalized = payload.replace(/-/g, "+").replace(/_/g, "/");
    const decoded = JSON.parse(Buffer.from(normalized, "base64").toString("utf8"));
    const exp = typeof decoded.exp === "number" ? decoded.exp : 0;

    return exp <= Math.floor(Date.now() / 1000) + 60;
  } catch {
    return true;
  }
}

export const { handlers, auth, signIn, signOut } = NextAuth({
  debug: process.env.AUTH_DEBUG === "true" && process.env.NODE_ENV !== "production",
  trustHost: true,
  providers: [
    Google({
      clientId: process.env.GOOGLE_CLIENT_ID,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET,
    }),
    Credentials({
      name: "Credentials",
      credentials: {
        email: { label: "Email", type: "email" },
        password: { label: "Password", type: "password" },
      },
      async authorize(credentials) {
        if (!credentials?.email || !credentials?.password) return null;
        
        try {
          const backendUrl = process.env.BACKEND_API_URL || "http://localhost:8080";
          const res = await fetch(`${backendUrl}/api/users/login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              email: credentials.email,
              password: credentials.password,
            }),
          });

          if (!res.ok) return null;
          const user = await res.json();
          
          return {
            id: user.id,
            email: user.email,
            name: user.name,
            userType: user.userType,
          };
        } catch (error) {
          console.error("Auth error:", error);
          return null;
        }
      },
    }),
  ],
  pages: {
    signIn: "/auth/login",
    newUser: "/auth/signup",
  },
  callbacks: {
    async jwt({ token, user, account, trigger, session }) {
      const secretKey = process.env.NEXTAUTH_SECRET || process.env.SECRET_KEY;
      const secret = new TextEncoder().encode(secretKey);

      if (user) {
        const appUser = user as AuthUserFields;
        token.id = user.id;
        token.userType = appUser.userType;
        token.name = appUser.name || user.name;
        token.email = user.email;
        token.provider = account?.provider;

        // For OAuth users (Google), try to fetch existing profile from DB
        if (account?.provider === "google" && !token.userType) {
          try {
            const backendUrl = process.env.BACKEND_API_URL || "http://localhost:8080";
            const res = await fetch(`${backendUrl}/api/users/profile-by-email/${user.email}`, {
              headers: {
                "X-Internal-Secret": secretKey as string,
              },
            });
            if (res.ok) {
              const dbUser = await res.json();
              token.id = dbUser.id; // Sync with DB ID
              token.userType = dbUser.userType;
              token.name = dbUser.name || token.name;
            }
          } catch (error) {
            console.error("OAuth profile fetch error:", error);
          }
        }
        
        token.accessToken = await signBackendToken(token.id, token.email, secret);
      }
      
      // Handle session update (manual trigger from client)
      if (trigger === "update") {
        if (session?.userType) token.userType = session.userType;
        if (session?.name) {
          token.name = session.name;
        }
        token.accessToken = await signBackendToken(token.id, token.email, secret);
      }
      
      // Repair missing or expired backend tokens in existing sessions.
      if (token.id && isBackendTokenExpired(token.accessToken)) {
        token.accessToken = await signBackendToken(token.id, token.email, secret);
      }
      
      return token;
    },
    async session({ session, token }) {
      if (session.user) {
        const mutableSession = session as MutableSession;
        mutableSession.user = session.user as AuthUserFields;
        mutableSession.user.id = token.id as string;
        mutableSession.user.userType = token.userType as string;
        mutableSession.user.accessToken = token.accessToken;
        mutableSession.provider = token.provider;
        session.user.name = token.name as string;
        
      }
      return session;
    },
  },
  session: {
    strategy: "jwt",
  },
  secret: process.env.NEXTAUTH_SECRET || process.env.SECRET_KEY,
});

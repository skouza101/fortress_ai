import NextAuth from "next-auth";
import Google from "next-auth/providers/google";
import Credentials from "next-auth/providers/credentials";
import { SignJWT } from "jose";

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
        // Credential auth is disabled until a real user/password backend is wired.
        return null;
      },
    }),
  ],
  pages: {
    signIn: "/auth/login",
    newUser: "/auth/signup",
  },
  callbacks: {
    async jwt({ token, user, trigger, session }) {
      const secretKey = process.env.NEXTAUTH_SECRET || process.env.SECRET_KEY;
      const secret = new TextEncoder().encode(secretKey);

      if (user) {
        token.id = user.id;
        token.userType = (user as any).userType;
        token.name = (user as any).name;
        token.email = user.email;
        
        // Sign a JWT for the backend
        token.accessToken = await new SignJWT({ sub: user.id, email: user.email })
          .setProtectedHeader({ alg: "HS256" })
          .setIssuedAt()
          .setExpirationTime("24h")
          .sign(secret);
        
      }
      
      // Handle session update (manual trigger from client)
      if (trigger === "update") {
        if (session?.userType) token.userType = session.userType;
        if (session?.name) {
          token.name = session.name;
        }
        // Always re-sign token on update to keep it fresh
        token.accessToken = await new SignJWT({ sub: token.id as string, email: token.email as string })
          .setProtectedHeader({ alg: "HS256" })
          .setIssuedAt()
          .setExpirationTime("24h")
          .sign(secret);
      }
      
      // Repair if missing (handles existing sessions)
      if (!token.accessToken && token.id) {
          token.accessToken = await new SignJWT({ sub: token.id as string, email: token.email as string })
            .setProtectedHeader({ alg: "HS256" })
            .setIssuedAt()
            .setExpirationTime("24h")
            .sign(secret);
      }
      
      return token;
    },
    async session({ session, token }) {
      if (session.user) {
        (session.user as any).id = token.id;
        (session.user as any).userType = token.userType;
        (session.user as any).accessToken = token.accessToken;
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

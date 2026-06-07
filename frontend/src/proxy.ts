import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'
import { clerkMiddleware, createRouteMatcher } from '@clerk/nextjs/server'

// Define which routes are public (don't require login)
const isPublicRoute = createRouteMatcher([
  "/",
  "/auth(.*)",
  "/status(.*)",
  "/api/public(.*)"
]);

const bypassAuth =
  process.env.FORTRESS_BYPASS_AUTH === 'true' ||
  !process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY ||
  !process.env.CLERK_SECRET_KEY;

export default clerkMiddleware(async (auth, request) => {
  if (bypassAuth) {
    return NextResponse.next();
  }

  if (!isPublicRoute(request)) {
    await auth.protect();
  }
});

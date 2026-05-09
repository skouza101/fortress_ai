import { auth } from "@/auth";
import { NextResponse } from "next/server";

export const proxy = auth((req) => {
  const path = req.nextUrl.pathname;
  const isPublicRoute =
    path === "/" ||
    path.startsWith("/auth") ||
    path.startsWith("/status") ||
    path.startsWith("/api/public") ||
    path.startsWith("/api/auth");
  const isApiRoute = path.startsWith("/api") || path.startsWith("/trpc");

  const isAuthenticated = !!req.auth;
  const hasUserType = !!(req.auth?.user as any)?.userType;
  const hasName = !!(req.auth?.user as any)?.name;
  const isOnboardingPage = path === "/auth/complete-profile";

  // 1. Redirect unauthenticated users to login
  if (!isAuthenticated && !isPublicRoute) {
    if (isApiRoute) {
      return NextResponse.json({ error: "Authentication required" }, { status: 401 });
    }
    const newUrl = new URL("/auth/login", req.nextUrl.origin);
    return NextResponse.redirect(newUrl);
  }

  // 2. Redirect authenticated users WITHOUT a userType OR Name to onboarding
  if (isAuthenticated && (!hasUserType || !hasName) && !isOnboardingPage && !isPublicRoute) {
    if (isApiRoute) {
      return NextResponse.json({ error: "Profile completion required" }, { status: 403 });
    }
    const newUrl = new URL("/auth/complete-profile", req.nextUrl.origin);
    return NextResponse.redirect(newUrl);
  }

  // 3. If they have everything and try to go to onboarding, send them to chat
  if (isAuthenticated && hasUserType && hasName && isOnboardingPage) {
    const newUrl = new URL("/chat", req.nextUrl.origin);
    return NextResponse.redirect(newUrl);
  }
});

export const config = {
  matcher: [
    // Skip Next.js internals and all static files, unless found in search params
    '/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)',
    // Always run for API routes
    '/(api|trpc)(.*)',
  ],
};

import { auth } from "@/auth";
import { NextResponse } from "next/server";

const PUBLIC_USER_API_ROUTES = new Set([
  "/api/users/signup",
  "/api/users/login",
  "/api/users/forgot-password",
  "/api/users/reset-password",
  "/api/users/verify-email",
]);

export const proxy = auth((req) => {
  const path = req.nextUrl.pathname;
  const isPublicRoute =
    path === "/" ||
    path.startsWith("/auth") ||
    path.startsWith("/status") ||
    path.startsWith("/api/public") ||
    path.startsWith("/api/auth") ||
    PUBLIC_USER_API_ROUTES.has(path);
  const isApiRoute = path.startsWith("/api") || path.startsWith("/trpc");

  const isAuthenticated = !!req.auth;

  // 1. Redirect unauthenticated users to login
  if (!isAuthenticated && !isPublicRoute) {
    if (isApiRoute) {
      return NextResponse.json({ error: "Authentication required" }, { status: 401 });
    }
    const newUrl = new URL("/auth/login", req.nextUrl.origin);
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

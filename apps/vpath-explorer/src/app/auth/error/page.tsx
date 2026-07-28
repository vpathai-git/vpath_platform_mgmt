import { AuthErrorPage } from "@vpath/sdk";

export default function AuthError() {
  return (
    <AuthErrorPage
      retryHref="/explorer/auth/signin"
      landingHref="/explorer"
      clearCookiesPath="/explorer/api/sso/clear-nextauth"
    />
  );
}

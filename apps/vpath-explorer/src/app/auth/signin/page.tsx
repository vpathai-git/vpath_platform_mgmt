import { SignInPage } from "@vpath/sdk";

type Props = {
  searchParams?: { callbackUrl?: string; error?: string };
};

export default function SignIn({ searchParams }: Props) {
  return (
    <SignInPage
      callbackUrl={searchParams?.callbackUrl ?? "/explorer/"}
      errorCode={searchParams?.error}
    />
  );
}

import { Suspense } from "react";
import { AuthForm } from "@/components/auth-form";

export const metadata = { title: "Masuk · Joblytic" };

export default function LoginPage() {
  return (
    <Suspense>
      <AuthForm mode="login" />
    </Suspense>
  );
}

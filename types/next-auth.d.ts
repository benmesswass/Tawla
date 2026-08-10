import type { DefaultSession } from "next-auth";
import type { Role } from "@/app/generated/prisma/enums";

declare module "@auth/core/types" {
  interface Session {
    user: {
      id: string;
      role: Role;
      restaurantId: string;
    } & DefaultSession["user"];
  }

  interface User {
    role: Role;
    restaurantId: string;
  }
}

declare module "@auth/core/jwt" {
  interface JWT {
    userId?: string;
    role?: Role;
    restaurantId?: string;
  }
}

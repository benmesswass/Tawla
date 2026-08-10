import type { NextAuthConfig } from "next-auth";

// Config Edge-safe (utilisée par le Middleware) : aucun provider nécessitant
// Prisma/bcrypt ici — ceux-ci ne tournent qu'en runtime Node (voir lib/auth.ts).
export const authConfig: NextAuthConfig = {
  session: { strategy: "jwt" },
  pages: { signIn: "/connexion" },
  trustHost: true,
  providers: [],
  callbacks: {
    jwt({ token, user }) {
      if (user) {
        token.userId = user.id;
        token.role = user.role;
        token.restaurantId = user.restaurantId;
      }
      return token;
    },
    session({ session, token }) {
      if (token.userId) session.user.id = token.userId;
      if (token.role) session.user.role = token.role;
      if (token.restaurantId) session.user.restaurantId = token.restaurantId;
      return session;
    },
  },
};

import NextAuth from "next-auth";
import Credentials from "next-auth/providers/credentials";
import bcrypt from "bcryptjs";
import { z } from "zod";
import { prisma } from "@/lib/prisma";
import { authConfig } from "@/lib/auth.config";

const credentialsSchema = z.object({
  email: z.string().email().max(200),
  password: z.string().min(8).max(200),
});

export const { handlers, auth, signIn, signOut } = NextAuth({
  ...authConfig,
  providers: [
    Credentials({
      credentials: { email: {}, password: {} },
      async authorize(credentials) {
        const parsed = credentialsSchema.safeParse(credentials);
        if (!parsed.success) return null;

        const user = await prisma.utilisateur.findUnique({
          where: { email: parsed.data.email.toLowerCase() },
        });

        if (!user) {
          // Coût constant : même en l'absence de compte, on compare contre un
          // hash bcrypt valide pour éviter de révéler l'existence du compte via le timing.
          await bcrypt.compare(
            parsed.data.password,
            "$2b$12$f/0oq4Vt.wjtcqw76TM1DONwSQqoVa/lcI0H/3sTvjhBSBTJBjYHG" // nosemgrep: generic.secrets.security.detected-bcrypt-hash.detected-bcrypt-hash
          );
          return null;
        }

        const valid = await bcrypt.compare(parsed.data.password, user.motDePasseHash);
        if (!valid) return null;

        return {
          id: user.id,
          name: user.nom,
          email: user.email,
          role: user.role,
          restaurantId: user.restaurantId,
        };
      },
    }),
  ],
});

import bcrypt from "bcryptjs";
import { PrismaClient } from "../app/generated/prisma/client";

const prisma = new PrismaClient();

const MOT_DE_PASSE_DEMO = "tawla2026";

async function main() {
  const motDePasseHash = await bcrypt.hash(MOT_DE_PASSE_DEMO, 10);

  const restaurant = await prisma.restaurant.upsert({
    where: { id: "resto-demo" },
    update: {},
    create: {
      id: "resto-demo",
      nom: "Dar Chaabane",
      ville: "Hammamet",
    },
  });

  await prisma.utilisateur.upsert({
    where: { email: "manager@tawla.tn" },
    update: {},
    create: {
      email: "manager@tawla.tn",
      motDePasseHash,
      nom: "Amine (manager)",
      role: "MANAGER",
      restaurantId: restaurant.id,
    },
  });

  await prisma.utilisateur.upsert({
    where: { email: "sami@tawla.tn" },
    update: {},
    create: {
      email: "sami@tawla.tn",
      motDePasseHash,
      nom: "Sami (serveur)",
      role: "SERVEUR",
      restaurantId: restaurant.id,
    },
  });

  await prisma.utilisateur.upsert({
    where: { email: "cuisine@tawla.tn" },
    update: {},
    create: {
      email: "cuisine@tawla.tn",
      motDePasseHash,
      nom: "Chef Karim",
      role: "CUISINE",
      restaurantId: restaurant.id,
    },
  });

  const categorie = await prisma.categorie.upsert({
    where: { id: "cat-demo-plats" },
    update: {},
    create: {
      id: "cat-demo-plats",
      nom: "Plats",
      ordre: 1,
      restaurantId: restaurant.id,
    },
  });

  await prisma.plat.upsert({
    where: { id: "plat-demo-couscous" },
    update: {},
    create: {
      id: "plat-demo-couscous",
      nom: "Couscous au poisson",
      description: "Couscous traditionnel, poisson du jour, légumes",
      prixMillimes: 22000,
      niveauPiment: 1,
      categorieId: categorie.id,
      restaurantId: restaurant.id,
    },
  });

  for (const numero of ["1", "2", "3"]) {
    await prisma.table.upsert({
      where: { restaurantId_numero: { restaurantId: restaurant.id, numero } },
      update: {},
      create: { numero, restaurantId: restaurant.id },
    });
  }

  console.log("Seed terminé — comptes démo (mot de passe: %s) :", MOT_DE_PASSE_DEMO);
  console.log("  manager@tawla.tn (MANAGER)");
  console.log("  sami@tawla.tn (SERVEUR)");
  console.log("  cuisine@tawla.tn (CUISINE)");
}

main()
  .catch((e) => {
    console.error(e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });

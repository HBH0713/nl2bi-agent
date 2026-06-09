import { defineConfig } from "prisma/config";

export default defineConfig({
  datasources: {
    db: {
      url: "postgresql://postgres:hbh5201314@db.zwpbndrpfonqpndjrwfp.supabase.co:5432/postgres",
    },
  },
});

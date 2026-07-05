import os from "node:os";

const lanHosts = Object.values(os.networkInterfaces())
  .flat()
  .filter((entry) => entry?.family === "IPv4" && !entry.internal)
  .map((entry) => entry.address);

/** @type {import('next').NextConfig} */
export default {
  allowedDevOrigins: ["127.0.0.1", "localhost", ...lanHosts],
};

import type { Config } from "tailwindcss";
const { sdkContent } = require("@vpath/sdk/tailwind.preset");

export default {
  presets: [require("@vpath/sdk/tailwind.preset")],
  content: ["./src/**/*.{ts,tsx,mdx}", sdkContent],
  theme: { extend: {} },
  plugins: [],
} satisfies Config;

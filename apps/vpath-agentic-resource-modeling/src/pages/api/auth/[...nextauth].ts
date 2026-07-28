// Auth is platform-owned (CLAUDE.md §3). The SDK builds the whole NextAuth
// handler + options; the app writes none of it. iframeCompatible: the app runs
// inside the platform shell iframe.
import { createNextAuthHandler } from "@vpath/sdk";

const { handler, options } = createNextAuthHandler({ iframeCompatible: true });

export { options as authOptions };
export default handler;

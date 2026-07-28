import { createNextAuthHandler } from "@vpath/sdk";

const { handler, options } = createNextAuthHandler({ iframeCompatible: true });

export { options as authOptions };
export default handler;

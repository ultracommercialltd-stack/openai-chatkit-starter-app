import { ChatKit, useChatKit } from "@openai/chatkit-react";
import { CHATKIT_API_DOMAIN_KEY, CHATKIT_API_URL } from "../lib/config";

/**
 * Demo panel for the LoveGenie ChatKit adapter.
 *
 * The adapter proxies to the locked Love-Genie backend, which requires auth.
 * For local testing, set these (optional) env vars in `.env.local` so the
 * starter can talk to Love-Genie as a real user:
 *   VITE_LG_DEV_BEARER     - a Supabase access token (paid user), OR
 *   VITE_LG_DEV_LEAD_TOKEN - a lead access token (free user)
 *   VITE_LG_ME_TYPE / VITE_LG_PARTNER_TYPE / VITE_LG_RESULT_ID - chat context
 *
 * These are attached to every /chatkit request via an `api.fetch` override —
 * the same mechanism LoveGenieApp uses, just sourced from env instead of the
 * live Supabase session.
 */
const env = import.meta.env as Record<string, string | undefined>;

function withLoveGenieHeaders(init: RequestInit | undefined): RequestInit {
  const headers = new Headers(init?.headers);
  const bearer = env.VITE_LG_DEV_BEARER;
  const leadToken = env.VITE_LG_DEV_LEAD_TOKEN;
  if (bearer) headers.set("Authorization", `Bearer ${bearer}`);
  else if (leadToken) headers.set("x-lead-token", leadToken);
  if (env.VITE_LG_RESULT_ID) headers.set("x-lg-result-id", env.VITE_LG_RESULT_ID);
  if (env.VITE_LG_ME_TYPE) headers.set("x-lg-me-type", env.VITE_LG_ME_TYPE);
  if (env.VITE_LG_PARTNER_TYPE) headers.set("x-lg-partner-type", env.VITE_LG_PARTNER_TYPE);
  return { ...init, headers };
}

export function ChatKitPanel() {
  const chatkit = useChatKit({
    api: {
      url: CHATKIT_API_URL,
      domainKey: CHATKIT_API_DOMAIN_KEY,
      fetch: (input, init) => fetch(input, withLoveGenieHeaders(init)),
    },
    theme: {
      colorScheme: "light",
      radius: "round",
      color: { accent: { primary: "#C9607A", level: 1 } },
    },
    composer: {
      placeholder: "What's going on? Paste the message or describe it…",
      // Screenshot ingestion is a later phase; disabled for the MVP.
      attachments: { enabled: false },
    },
    startScreen: {
      greeting: "What's going on with them today?",
      prompts: [
        { label: "They left me on read", prompt: "They left me on read and I don't know what to send." },
        { label: "We argued", prompt: "We argued and I don't know how to fix it." },
        { label: "Mixed signals", prompt: "I'm getting mixed signals and can't tell what they want." },
        { label: "What do I text back?", prompt: "Here's their last message — what should I text back?" },
      ],
    },
  });

  return (
    <div className="relative pb-8 flex h-[90vh] w-full rounded-2xl flex-col overflow-hidden bg-white shadow-sm transition-colors dark:bg-slate-900">
      <ChatKit control={chatkit.control} className="block h-full w-full" />
    </div>
  );
}

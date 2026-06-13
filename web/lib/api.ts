"use client";

import { supabase } from "./supabaseClient";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL as string;

export interface Source {
  interaction_id: string;
  snippet: string;
}

export interface QueryResult {
  answer: string;
  sources: Source[];
}

/** Ask the brain. Sends the user's Supabase access token as a Bearer to the API. */
export async function askBrain(question: string): Promise<QueryResult> {
  const {
    data: { session },
  } = await supabase.auth.getSession();
  if (!session) {
    throw new Error("Not signed in");
  }

  const res = await fetch(`${API_BASE}/brain/query`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${session.access_token}`,
    },
    body: JSON.stringify({ question }),
  });

  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`Query failed (${res.status}): ${detail}`);
  }
  return (await res.json()) as QueryResult;
}

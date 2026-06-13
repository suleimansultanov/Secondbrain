"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabaseClient";
import { askBrain, type QueryResult } from "@/lib/api";

export default function AskPage() {
  const router = useRouter();
  const [ready, setReady] = useState(false);
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState<QueryResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // Guard: must be signed in.
  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (!session) {
        router.replace("/login");
      } else {
        setReady(true);
      }
    });
  }, [router]);

  async function onAsk(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      setResult(await askBrain(question));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  async function signOut() {
    await supabase.auth.signOut();
    router.replace("/login");
  }

  if (!ready) {
    return (
      <main className="container">
        <p className="muted">Loading…</p>
      </main>
    );
  }

  return (
    <main className="container">
      <div className="row">
        <div>
          <h1>Ask your company brain</h1>
          <p className="muted">Answers are grounded in your data, with sources.</p>
        </div>
        <button onClick={signOut} style={{ background: "transparent", border: "1px solid var(--border)" }}>
          Sign out
        </button>
      </div>

      <form onSubmit={onAsk} style={{ marginTop: 20 }}>
        <textarea
          placeholder="e.g. What did we promise Acme about delivery and pricing?"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          required
        />
        <button type="submit" disabled={loading || !question.trim()}>
          {loading ? "Thinking…" : "Ask"}
        </button>
      </form>

      {error && <p className="error">{error}</p>}

      {result && (
        <>
          <div className="answer">{result.answer}</div>
          {result.sources.length > 0 && (
            <>
              <p className="muted" style={{ marginTop: 20 }}>
                Sources
              </p>
              {result.sources.map((s, i) => (
                <div className="source" key={s.interaction_id + i}>
                  <strong>[{i + 1}]</strong> {s.snippet}
                </div>
              ))}
            </>
          )}
        </>
      )}
    </main>
  );
}

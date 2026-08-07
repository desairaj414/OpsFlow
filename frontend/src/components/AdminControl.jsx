"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function AdminControl({ token, apiBase }) {
  const [status, setStatus] = useState("checking...");
  const [username, setUsername] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function checkHealthAndUser() {
      try {
        const healthRes = await fetch(`${apiBase}/health`);
        const health = await healthRes.json();

        const meRes = await fetch(`${apiBase}/auth/me`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        const me = meRes.ok ? await meRes.json() : null;

        if (!cancelled) {
          setStatus(health.status === "ok" ? "Backend healthy" : "Backend unreachable");
          if (me) setUsername(me.username);
        }
      } catch {
        if (!cancelled) setStatus("Backend unreachable");
      }
    }

    checkHealthAndUser();
    return () => {
      cancelled = true;
    };
  }, [apiBase, token]);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Admin / Session Info</CardTitle>
        <CardDescription>Placeholder panel — extend per the event's PRD.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-1 text-sm">
        <p>Status: {status}</p>
        {username && <p>Signed in as: {username}</p>}
      </CardContent>
    </Card>
  );
}

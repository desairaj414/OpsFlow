"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import AdminControl from "@/components/AdminControl.jsx";

export default function Dashboard({ token, apiBase, onLogout }) {
  const [message, setMessage] = useState("");
  const [reply, setReply] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function sendMessage(e) {
    e.preventDefault();
    setLoading(true);
    setError("");
    setReply("");
    try {
      const res = await fetch(`${apiBase}/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ message }),
      });
      if (!res.ok) throw new Error(`Request failed (${res.status})`);
      const data = await res.json();
      setReply(data.reply);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6 p-8">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Dashboard</h1>
        <Button variant="outline" onClick={onLogout}>
          Log out
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Chat with the enterprise LLM</CardTitle>
        </CardHeader>
        <CardContent>
          <form className="flex gap-2" onSubmit={sendMessage}>
            <Input
              placeholder="Ask something..."
              value={message}
              onChange={(e) => setMessage(e.target.value)}
            />
            <Button type="submit" disabled={loading || !message}>
              {loading ? "Sending..." : "Send"}
            </Button>
          </form>
          {error && <p className="mt-3 text-sm text-red-500">{error}</p>}
          {reply && <p className="mt-4 whitespace-pre-wrap text-sm">{reply}</p>}
        </CardContent>
      </Card>

      <AdminControl token={token} apiBase={apiBase} />
    </div>
  );
}

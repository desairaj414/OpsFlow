"use client";

import { useEffect, useState } from "react";

// Local ITSM/Jira-shaped ticket history (GET /tickets) — lives at CockpitShell level so both Ops
// Board (Diagnose/Run-all/Ticket History) and the header's notification bell share one fetch and
// one "is this CI already ticketed" source of truth.
export function useTickets(apiBase, token) {
  const [tickets, setTickets] = useState([]);
  const [error, setError] = useState("");

  async function refetch() {
    try {
      const res = await fetch(`${apiBase}/tickets`, { headers: { Authorization: `Bearer ${token}` } });
      if (!res.ok) throw new Error(`Request failed (${res.status})`);
      setTickets((await res.json()).tickets);
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => {
    refetch();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [apiBase, token]);

  return { tickets, error, refetch };
}

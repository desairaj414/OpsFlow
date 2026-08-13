"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { ROLE_LABELS } from "@/lib/roles";
import { apiFetch } from "@/lib/api.js";

// User Management (admin-only): real accounts hitting the `users` table with a real PBKDF2
// password hash (auth_utils.py) — no mock data. Runbook/KB-article upload used to live in this
// panel too but duplicated the Knowledge Base tab's own upload controls (ChunkInspector.jsx), so
// that content stays there and this panel is users only.
export default function UserManagementPanel({ apiBase, token }) {
  const [users, setUsers] = useState([]);
  const [usersError, setUsersError] = useState("");
  const [newUsername, setNewUsername] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [newDisplayName, setNewDisplayName] = useState("");
  const [newRole, setNewRole] = useState("ops_engineer");
  const [creating, setCreating] = useState(false);

  async function loadUsers() {
    try {
      const res = await apiFetch(apiBase, "/users", { token });
      if (!res.ok) throw new Error(`Request failed (${res.status})`);
      setUsers(await res.json());
    } catch (err) {
      setUsersError(err.message);
    }
  }

  useEffect(() => {
    loadUsers();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [apiBase, token]);

  async function createUser() {
    if (!newUsername.trim() || !newDisplayName.trim() || newPassword.length < 8) return;
    setCreating(true);
    setUsersError("");
    try {
      const res = await apiFetch(apiBase, "/users", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        token,
        body: JSON.stringify({ username: newUsername, password: newPassword, display_name: newDisplayName, role: newRole }),
      });
      if (!res.ok) {
        const detail = await res.json().catch(() => ({}));
        throw new Error(detail.detail || `Request failed (${res.status})`);
      }
      setNewUsername("");
      setNewPassword("");
      setNewDisplayName("");
      await loadUsers();
    } catch (err) {
      setUsersError(err.message);
    } finally {
      setCreating(false);
    }
  }

  async function deleteUser(id) {
    setUsersError("");
    const res = await apiFetch(apiBase, `/users/${id}`, { method: "DELETE", token });
    if (!res.ok) {
      const detail = await res.json().catch(() => ({}));
      setUsersError(detail.detail || `Request failed (${res.status})`);
      return;
    }
    await loadUsers();
  }

  return (
    <div className="space-y-2 text-xs">
      <p className="mb-2 text-muted-foreground">Real accounts — each gets its own password, hashed (PBKDF2), and a fixed role.</p>
      {usersError && <p className="text-red-500">{usersError}</p>}
      <div className="space-y-1.5">
        {users.map((u) => (
          <div key={u.id} className="flex items-center justify-between gap-2 rounded-md border border-border p-2">
            <span>
              {u.display_name} <span className="text-muted-foreground">— {u.username} · {ROLE_LABELS[u.role] || u.role}</span>
            </span>
            <button className="text-muted-foreground hover:text-red-500" onClick={() => deleteUser(u.id)}>
              Remove
            </button>
          </div>
        ))}
      </div>
      <div className="mt-2 space-y-1.5 rounded-md border border-border p-2">
        <input
          className="w-full rounded-md border border-border bg-background px-2 py-1 focus:border-accent focus:outline-none"
          placeholder="Display name"
          value={newDisplayName}
          onChange={(e) => setNewDisplayName(e.target.value)}
        />
        <input
          className="w-full rounded-md border border-border bg-background px-2 py-1 focus:border-accent focus:outline-none"
          placeholder="Username"
          value={newUsername}
          onChange={(e) => setNewUsername(e.target.value)}
        />
        <input
          type="password"
          className="w-full rounded-md border border-border bg-background px-2 py-1 focus:border-accent focus:outline-none"
          placeholder="Password (min 8 characters)"
          value={newPassword}
          onChange={(e) => setNewPassword(e.target.value)}
        />
        <div className="flex gap-1.5">
          <select
            className="flex-1 rounded-md border border-border bg-background px-1 py-1"
            value={newRole}
            onChange={(e) => setNewRole(e.target.value)}
          >
            {Object.entries(ROLE_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
          <Button size="sm" onClick={createUser} disabled={creating}>
            Add user
          </Button>
        </div>
      </div>
    </div>
  );
}

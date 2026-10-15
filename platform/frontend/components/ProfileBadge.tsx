"use client";

import { useEffect, useState } from "react";
import { API_URL } from "@/lib/api";

/** Active benchmark profile chip (domain vocabulary from the backend). */

interface ProfileSummary {
  name: string;
  version: number;
  n_tasks: number;
}

export function ProfileBadge() {
  const [profile, setProfile] = useState<ProfileSummary | null>(null);
  useEffect(() => {
    fetch(`${API_URL}/profile`, { cache: "no-store" })
      .then((r) => (r.ok ? r.json() : null))
      .then(setProfile)
      .catch(() => setProfile(null));
  }, []);
  if (!profile) return null;
  return (
    <span className="rounded-full border border-emerald-300 px-2 py-0.5 font-mono text-xs text-emerald-700 dark:border-emerald-900 dark:text-emerald-400">
      {profile.name} · {profile.n_tasks} tasks
    </span>
  );
}

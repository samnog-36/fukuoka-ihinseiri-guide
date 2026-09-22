import { getSearchConsoleDashboard } from "../../_lib/google.js";

const REPO = "samnog-36/fukuoka-ihinseiri-guide";

function ghHeaders(env) {
  const h = {
    "accept": "application/vnd.github+json",
    "user-agent": "fukuoka-ihinseiri-admin-dashboard"
  };
  if (env.GITHUB_DASHBOARD_TOKEN) h.authorization = "Bearer " + env.GITHUB_DASHBOARD_TOKEN;
  return h;
}

async function gh(path, env) {
  const res = await fetch("https://api.github.com/repos/" + REPO + path, {
    headers: ghHeaders(env),
    cf: { cacheTtl: 60 }
  });
  if (!res.ok) throw new Error("github_api_failed:" + res.status);
  return res.json();
}

async function activity() {
  const res = await fetch(
    "https://raw.githubusercontent.com/" + REPO + "/main/data/ai-activity-log.json",
    { cf: { cacheTtl: 60 } }
  );
  if (!res.ok) return [];
  const data = await res.json();
  return Array.isArray(data) ? data : [];
}

export async function onRequestGet(context) {
  const { env } = context;
  const output = {
    generatedAt: new Date().toISOString(),
    schedule: { timezone: "Asia/Tokyo", localTime: "05:10", cadence: "daily" }
  };

  const [runsResult, pullsResult, commitsResult, activityResult, gscResult] = await Promise.allSettled([
    gh("/actions/workflows/content-growth-os.yml/runs?per_page=20", env),
    gh("/pulls?state=all&sort=updated&direction=desc&per_page=20", env),
    gh("/commits?sha=main&per_page=12", env),
    activity(),
    getSearchConsoleDashboard(env)
  ]);

  output.github = {
    configured: true,
    runs: runsResult.status === "fulfilled"
      ? (runsResult.value.workflow_runs || []).map(r => ({
          id: r.id,
          status: r.status,
          conclusion: r.conclusion,
          event: r.event,
          createdAt: r.created_at,
          updatedAt: r.updated_at,
          url: r.html_url,
          title: r.display_title,
          sha: r.head_sha
        }))
      : [],
    pulls: pullsResult.status === "fulfilled"
      ? pullsResult.value.map(p => ({
          number: p.number,
          state: p.state,
          mergedAt: p.merged_at,
          title: p.title,
          url: p.html_url,
          createdAt: p.created_at,
          updatedAt: p.updated_at,
          user: p.user?.login || ""
        }))
      : [],
    commits: commitsResult.status === "fulfilled"
      ? commitsResult.value.map(c => ({
          sha: c.sha,
          message: c.commit?.message || "",
          date: c.commit?.committer?.date || "",
          url: c.html_url
        }))
      : []
  };

  output.activity = activityResult.status === "fulfilled" ? activityResult.value : [];
  output.gsc = gscResult.status === "fulfilled"
    ? gscResult.value
    : { configured: Boolean(env.GOOGLE_SERVICE_ACCOUNT_JSON), error: String(gscResult.reason || "unknown") };

  output.health = {
    googleCredentialConfigured: Boolean(env.GOOGLE_SERVICE_ACCOUNT_JSON),
    searchConsoleSiteConfigured: Boolean(env.SEARCH_CONSOLE_SITE_URL),
    githubTokenConfigured: Boolean(env.GITHUB_DASHBOARD_TOKEN),
    databaseConfigured: Boolean(env.DB),
    accessConfigured: Boolean(env.CF_ACCESS_TEAM_DOMAIN && env.CF_ACCESS_AUD),
    ownerEmailLocked: true
  };

  return new Response(JSON.stringify(output), {
    headers: {
      "content-type": "application/json; charset=utf-8",
      "cache-control": "no-store"
    }
  });
}

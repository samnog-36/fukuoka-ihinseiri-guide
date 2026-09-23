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

function nextDailyJst(hour = 5, minute = 10) {
  const now = new Date();
  const jst = new Date(now.getTime() + 9 * 60 * 60 * 1000);
  let target = new Date(Date.UTC(
    jst.getUTCFullYear(),
    jst.getUTCMonth(),
    jst.getUTCDate(),
    hour - 9,
    minute,
    0
  ));
  if (target <= now) {
    target = new Date(Date.UTC(
      jst.getUTCFullYear(),
      jst.getUTCMonth(),
      jst.getUTCDate() + 1,
      hour - 9,
      minute,
      0
    ));
  }
  return target.toISOString();
}

export async function onRequestGet(context) {
  const { env } = context;
  const output = {
    generatedAt: new Date().toISOString(),
    schedule: {
      timezone: "Asia/Tokyo",
      localTime: "05:10",
      cadence: "daily",
      nextRunAt: nextDailyJst(5, 10)
    }
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

  const runs = output.github.runs || [];
  const latestRun = runs[0] || null;
  const activities = output.activity || [];
  const latestPublished = activities[0] || null;
  const latestRunActivity = latestRun
    ? activities.find(a => String(a.run_id || "") === String(latestRun.id))
    : null;

  output.automation = {
    status: latestRun && latestRun.status !== "completed" ? latestRun.status : "waiting",
    mode: "improve",
    nextRunAt: output.schedule.nextRunAt,
    latestRun,
    latestPublished,
    latestRunActivity,
    maxPublicationsPerRun: 1,
    minimumReviewerScore: 88,
    pipeline: [
      "Search Console取得",
      "改善候補を選定",
      "Editor AIが一次情報を調査・編集",
      "独立Reviewer AIが再検証",
      "品質・AdSense・HTML Gate",
      "合格時のみmainへ自動反映"
    ]
  };

  output.health = {
    googleCredentialConfigured: Boolean(env.GOOGLE_SERVICE_ACCOUNT_JSON),
    searchConsoleSiteConfigured: Boolean(env.SEARCH_CONSOLE_SITE_URL),
    githubApiReachable: runsResult.status === "fulfilled" || commitsResult.status === "fulfilled",
    databaseConfigured: Boolean(env.DB),
    accessConfigured: Boolean(env.CF_ACCESS_TEAM_DOMAIN && env.CF_ACCESS_AUD),
    ownerEmailLocked: true
  };

  output.optional = {
    githubDashboardTokenConfigured: Boolean(env.GITHUB_DASHBOARD_TOKEN),
    githubDashboardTokenNote: "公開リポジトリのため未設定でも現在のダッシュボード取得は動作します。APIレート上限を増やしたい場合のみ設定します。"
  };

  return new Response(JSON.stringify(output), {
    headers: {
      "content-type": "application/json; charset=utf-8",
      "cache-control": "no-store"
    }
  });
}

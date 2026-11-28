// 크롬 API를 쓰지 않는 순수 함수 모음.
// src/magami/extract.py의 parse_response · make_id · make_notice와 같은 규칙을 따른다.

const MAGAMI = (() => {
  const AI_FIELDS = [
    "is_notice", "title", "apply_start", "apply_end",
    "deadline", "deadline_time", "target", "how_to_apply",
  ];
  const SCHEMA_ORDER = ["id", "source", "channel", "url", "posted_at", ...AI_FIELDS, "collected_at"];

  const DATE_RE = /^\s*(\d{4})\s*[-./년]\s*(\d{1,2})\s*[-./월]\s*(\d{1,2})\s*일?\s*$/;
  const TIME_RE = /^\s*(\d{1,2})\s*[:시]\s*(\d{2})?\s*분?\s*$/;

  const pad = (n) => String(n).padStart(2, "0");

  function normalizeDate(value) {
    if (value === null || value === undefined) return null;
    const m = DATE_RE.exec(String(value));
    if (!m) return null;
    const y = Number(m[1]), mo = Number(m[2]), d = Number(m[3]);
    const dt = new Date(Date.UTC(y, mo - 1, d));
    if (dt.getUTCFullYear() !== y || dt.getUTCMonth() !== mo - 1 || dt.getUTCDate() !== d) return null;
    return `${y}-${pad(mo)}-${pad(d)}`;
  }

  function normalizeTime(value) {
    if (value === null || value === undefined) return null;
    const m = TIME_RE.exec(String(value));
    if (!m) return null;
    let h = Number(m[1]), mi = Number(m[2] || 0);
    if (h > 24 || mi > 59) return null;
    if (h === 24) { h = 23; mi = 59; }
    return `${pad(h)}:${pad(mi)}`;
  }

  function cleanText(value) {
    if (value === null || value === undefined) return null;
    const text = String(value).split(/\s+/).filter(Boolean).join(" ");
    if (!text || ["null", "none"].includes(text.toLowerCase())) return null;
    return text;
  }

  function toBool(value) {
    if (typeof value === "boolean") return value;
    return ["true", "1", "yes", "y"].includes(String(value).trim().toLowerCase());
  }

  function parseResponse(raw) {
    let text = String(raw).trim();
    const fence = /```(?:json)?\s*(\{[\s\S]*\})\s*```/.exec(text);
    if (fence) {
      text = fence[1];
    } else {
      const s = text.indexOf("{"), e = text.lastIndexOf("}");
      if (s === -1 || e === -1) throw new Error("AI 응답에서 JSON을 찾지 못했습니다.");
      text = text.slice(s, e + 1);
    }
    const data = JSON.parse(text);
    const f = {
      is_notice: toBool(data.is_notice),
      title: cleanText(data.title),
      apply_start: normalizeDate(data.apply_start),
      apply_end: normalizeDate(data.apply_end),
      deadline: normalizeDate(data.deadline),
      deadline_time: normalizeTime(data.deadline_time),
      target: cleanText(data.target),
      how_to_apply: cleanText(data.how_to_apply),
    };
    if (f.deadline === null && f.apply_end) f.deadline = f.apply_end;
    if (!f.is_notice) {
      for (const k of AI_FIELDS) if (k !== "is_notice" && k !== "title") f[k] = null;
    }
    return f;
  }

  async function sha1Hex(text) {
    const buf = await crypto.subtle.digest("SHA-1", new TextEncoder().encode(text));
    return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("");
  }

  async function makeId(url) {
    if (!url) return "unknown_" + Date.now();
    const u = new URL(url);
    const parts = u.pathname.split("/").filter(Boolean);
    if (u.hostname.includes("instagram.com") && parts.length >= 2 && ["p", "reel"].includes(parts[0])) {
      return `instagram_${parts[1]}`;
    }
    const ntt = u.searchParams.get("nttSn");
    if (ntt) return `homepage_${parts[0] || "main"}_${ntt}`;
    return "web_" + (await sha1Hex(url)).slice(0, 10);
  }

  // 한국 시간 기준 ISO 문자열 (예: 2026-11-27T09:00:00+09:00)
  function nowKst(date = new Date()) {
    const k = new Date(date.getTime() + 9 * 3600 * 1000);
    return `${k.getUTCFullYear()}-${pad(k.getUTCMonth() + 1)}-${pad(k.getUTCDate())}` +
      `T${pad(k.getUTCHours())}:${pad(k.getUTCMinutes())}:${pad(k.getUTCSeconds())}+09:00`;
  }

  function todayKst(date = new Date()) {
    return nowKst(date).slice(0, 10);
  }

  async function makeNotice(fields, { url, channel = null, postedAt = null, source = "extension" }) {
    const notice = {
      id: await makeId(url),
      source,
      channel,
      url,
      posted_at: normalizeDate(postedAt),
      collected_at: nowKst(),
    };
    for (const k of AI_FIELDS) notice[k] = fields[k] ?? null;
    const ordered = {};
    for (const k of SCHEMA_ORDER) ordered[k] = notice[k];
    return ordered;
  }

  function buildUserMessage(text, { url, postedAt, today }) {
    const lines = ["## 공지"];
    if (url) lines.push(`- 원문 링크: ${url}`);
    if (postedAt) lines.push(`- 게시일: ${postedAt}`);
    lines.push(`- 오늘 날짜: ${today}`);
    lines.push("- 본문:");
    lines.push(String(text).trim());
    return lines.join("\n");
  }

  function addDays(isoDate, days) {
    const [y, m, d] = isoDate.split("-").map(Number);
    const dt = new Date(Date.UTC(y, m - 1, d + days));
    return `${dt.getUTCFullYear()}${pad(dt.getUTCMonth() + 1)}${pad(dt.getUTCDate())}`;
  }

  // 구글 캘린더 "일정 추가" 화면 링크. 로그인 연동 없이 사용자가 직접 저장한다.
  function calendarUrl(notice) {
    if (!notice.deadline) return null;
    const ymd = notice.deadline.replaceAll("-", "");
    let dates;
    if (notice.deadline_time) {
      const [h, mi] = notice.deadline_time.split(":");
      dates = `${ymd}T${h}${mi}00/${ymd}T${h}${mi}00`;
    } else {
      dates = `${ymd}/${addDays(notice.deadline, 1)}`;
    }
    const details = [
      notice.apply_start || notice.apply_end
        ? `신청 기간: ${notice.apply_start || "?"} ~ ${notice.apply_end || "?"}` : null,
      notice.target ? `대상: ${notice.target}` : null,
      notice.how_to_apply ? `신청 방법: ${notice.how_to_apply}` : null,
      notice.url ? `원문: ${notice.url}` : null,
      "마감이로 정리함 — 원문과 꼭 대조하세요.",
    ].filter(Boolean).join("\n");
    const params = new URLSearchParams({
      action: "TEMPLATE",
      text: `[마감] ${notice.title || "공지"}`,
      dates,
      details,
      ctz: "Asia/Seoul",
    });
    return `https://calendar.google.com/calendar/render?${params.toString()}`;
  }

  return {
    AI_FIELDS, SCHEMA_ORDER, normalizeDate, normalizeTime, parseResponse,
    makeId, makeNotice, buildUserMessage, calendarUrl, nowKst, todayKst,
  };
})();

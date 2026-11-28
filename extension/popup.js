// 팝업: 사용자가 버튼을 누를 때만 지금 탭 하나를 읽고 Gemini로 정리한다.
// 공지 목록을 돌거나 다른 페이지를 열거나 새로 내려받는 기능은 없다 (docs/collection-policy.md).
//
// 흐름 (설예인 교수님 11/10 제안과 같은 순서)
//   ① 사용자가 공지를 연다 → ② 버튼 → ③ 제목·본문·주소(+포스터)를 읽어 추출
//   → ④ 사용자가 결과를 확인·수정하고 저장 → 내 마감 목록 · 구글 캘린더 · JSON

const DEFAULT_MODEL = "gemini-2.5-flash";
const MAX_TEXT = 15000;   // AI에 보낼 본문 최대 글자 수
const MAX_IMAGES = 3;     // AI에 보낼 포스터 이미지 최대 장수
const SAVED_KEY = "savedNotices";

const $ = (id) => document.getElementById(id);
const form = $("result");
let currentNotice = null;

function showStatus(message, isError = false) {
  const el = $("status");
  el.textContent = message;
  el.classList.toggle("error", isError);
  el.hidden = !message;
}

// ---------------------------------------------------------------- 웹페이지 안에서 실행되는 함수
// 사용자가 이미 연 페이지만 읽는다. 아무것도 새로 내려받지 않고 저장하지 않는다.
function readCurrentPage(maxText, maxImages, withImages) {
  const clean = (s) => String(s || "").replace(/[ \t]+\n/g, "\n").replace(/\n{3,}/g, "\n\n").trim();
  let title = document.title;
  let text = "";
  let method = "selector";

  // 1) Mozilla Readability로 본문 찾기 (복사본에 실행해 실제 페이지는 건드리지 않음)
  try {
    if (typeof Readability === "function") {
      const article = new Readability(document.cloneNode(true)).parse();
      if (article && article.textContent && article.textContent.trim().length > 50) {
        title = article.title || title;
        // 문단·줄바꿈을 살려서 글자만 꺼낸다 (DOMParser는 스크립트를 실행하지 않음)
        const html = article.content.replace(/<(br|\/p|\/div|\/li|\/h[1-6]|\/tr)[^>]*>/gi, (m) => m + "\n");
        text = new DOMParser().parseFromString(html, "text/html").body.textContent;
        method = "readability";
      }
    }
  } catch (e) { /* 실패하면 아래 방식으로 */ }

  // 2) 안 되면 흔한 본문 위치 → 그래도 없으면 페이지 전체
  if (!text) {
    const selectors = [".view-con", ".view_con", ".view_cont", ".bbs_view", ".board-view",
      ".board_view", "article", "#content", "main"];
    let node = null;
    for (const s of selectors) {
      const found = document.querySelector(s);
      if (found && found.innerText.trim().length > 50) { node = found; break; }
    }
    text = (node || document.body).innerText;
    method = node ? "selector" : "body";
  }

  // 3) 포스터: 이미 화면에 불러온 큰 이미지를 캔버스로 옮겨 담는다 (새 요청 없음)
  const images = [];
  let skipped = 0;
  if (withImages) {
    const candidates = [...document.images]
      .filter((img) => img.complete && img.naturalWidth >= 300 && img.naturalHeight >= 300)
      .filter((img) => !img.closest("header, nav, footer, aside"))
      .sort((a, b) => b.naturalWidth * b.naturalHeight - a.naturalWidth * a.naturalHeight);
    for (const img of candidates) {
      if (images.length >= maxImages) break;
      try {
        const scale = Math.min(1, 1600 / Math.max(img.naturalWidth, img.naturalHeight));
        const canvas = document.createElement("canvas");
        canvas.width = Math.round(img.naturalWidth * scale);
        canvas.height = Math.round(img.naturalHeight * scale);
        canvas.getContext("2d").drawImage(img, 0, 0, canvas.width, canvas.height);
        images.push(canvas.toDataURL("image/jpeg", 0.85).split(",")[1]);
      } catch (e) {
        skipped += 1; // 다른 사이트에서 불러온 이미지는 읽을 수 없음
      }
    }
  }

  // 게시판 글 제목은 보통 본문 위 제목 태그에 있어서 Readability가 빼는 경우가 있다 → 따로 모은다
  const headings = [...document.querySelectorAll("h1, h2, h3, h4")]
    .filter((h) => !h.closest("header, nav, footer, aside"))
    .map((h) => h.innerText.trim())
    .filter((t) => t.length >= 5 && t.length <= 150)
    .slice(0, 5);

  return { title, headings, url: location.href, text: clean(text).slice(0, maxText), method, images, skipped };
}

// ---------------------------------------------------------------- 설정 · AI 호출
async function getSettings() {
  const { apiKey = "", model = "" } = await chrome.storage.local.get(["apiKey", "model"]);
  return { apiKey: apiKey.trim(), model: model.trim() || DEFAULT_MODEL };
}

async function callGemini({ apiKey, model, prompt, message, images }) {
  const parts = [{ text: message }, ...images.map((img) => ({ inlineData: img }))];
  const res = await fetch(
    `https://generativelanguage.googleapis.com/v1beta/models/${encodeURIComponent(model)}:generateContent`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json", "x-goog-api-key": apiKey },
      body: JSON.stringify({
        systemInstruction: { parts: [{ text: prompt }] },
        contents: [{ role: "user", parts }],
        generationConfig: { responseMimeType: "application/json", temperature: 0 },
      }),
    },
  );
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const reason = data.error?.message || res.statusText;
    throw new Error(`Gemini 호출 실패 (${res.status}): ${reason}`);
  }
  const text = data.candidates?.[0]?.content?.parts?.map((p) => p.text || "").join("");
  if (!text) throw new Error("Gemini가 빈 응답을 보냈습니다.");
  return text;
}

function channelOf(url) {
  try {
    const u = new URL(url);
    const first = u.pathname.split("/").filter(Boolean)[0];
    return first ? `${u.hostname}/${first}` : u.hostname;
  } catch {
    return null;
  }
}

// ---------------------------------------------------------------- 결과 확인·수정
const FIELDS = ["title", "deadline", "deadline_time", "apply_start", "apply_end", "target", "how_to_apply"];

function fillForm(notice) {
  for (const key of FIELDS) form.elements[key].value = notice[key] || "";
  $("r-url").href = notice.url;
  $("not-notice").hidden = notice.is_notice;
}

function readForm() {
  return Object.fromEntries(FIELDS.map((k) => [k, form.elements[k].value.trim()]));
}

function refreshLinks() {
  currentNotice = MAGAMI.applyEdits(currentNotice, readForm());
  const cal = $("add-calendar");
  const link = MAGAMI.calendarUrl(currentNotice);
  if (link) {
    cal.href = link;
    cal.classList.remove("disabled");
    cal.title = "";
  } else {
    cal.removeAttribute("href");
    cal.classList.add("disabled");
    cal.title = "마감일을 넣어야 캘린더에 추가할 수 있습니다";
  }
}

// ---------------------------------------------------------------- 내 마감 목록
async function loadSaved() {
  const { [SAVED_KEY]: list = [] } = await chrome.storage.local.get(SAVED_KEY);
  return list;
}

async function saveList(list) {
  await chrome.storage.local.set({ [SAVED_KEY]: list });
  $("saved-count").textContent = list.length ? `(${list.length})` : "";
}

async function renderSaved() {
  const list = await loadSaved();
  const today = MAGAMI.todayKst();
  const ul = $("saved-list");
  ul.textContent = "";
  if (!list.length) {
    const li = document.createElement("li");
    li.textContent = "아직 저장한 공지가 없습니다.";
    ul.append(li);
  }
  for (const n of list) {
    const left = MAGAMI.daysLeft(n.deadline, today);
    const li = document.createElement("li");

    const dday = document.createElement("span");
    dday.className = "dday" + (left !== null && left < 0 ? " past" : left !== null && left <= 3 ? " soon" : "");
    dday.textContent = left === null ? "미정" : left === 0 ? "D-DAY" : left > 0 ? `D-${left}` : "마감";
    const title = document.createElement("a");
    title.href = n.url;
    title.target = "_blank";
    title.rel = "noopener";
    title.textContent = n.title || "(제목 없음)";
    const meta = document.createElement("div");
    meta.className = "meta";
    meta.textContent = `마감 ${n.deadline || "미정"}${n.deadline_time ? " " + n.deadline_time : ""}`;

    const actions = document.createElement("div");
    actions.className = "actions";
    const cal = MAGAMI.calendarUrl(n);
    if (cal) {
      const a = document.createElement("a");
      a.href = cal;
      a.target = "_blank";
      a.rel = "noopener";
      a.textContent = "캘린더에 추가";
      actions.append(a);
    }
    const del = document.createElement("button");
    del.type = "button";
    del.textContent = "삭제";
    del.addEventListener("click", async () => {
      await saveList((await loadSaved()).filter((x) => x.id !== n.id));
      renderSaved();
    });
    actions.append(del);

    li.append(dday, title, meta, actions);
    ul.append(li);
  }
}

// ---------------------------------------------------------------- 실행
async function run() {
  $("run").disabled = true;
  form.hidden = true;
  $("saved").hidden = true;
  try {
    const { apiKey, model } = await getSettings();
    if (!apiKey) {
      showStatus("먼저 설정에서 Gemini API 키를 넣어 주세요.", true);
      return;
    }
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab || !/^https?:/.test(tab.url || "")) {
      showStatus("일반 웹페이지(공지 글)에서 눌러 주세요.", true);
      return;
    }

    showStatus("공지를 읽는 중…");
    const withImages = $("with-images").checked;
    await chrome.scripting.executeScript({ target: { tabId: tab.id }, files: ["vendor/Readability.js"] });
    const [{ result: page }] = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: readCurrentPage,
      args: [MAX_TEXT, MAX_IMAGES, withImages],
    });

    let images = page.images.map((data) => ({ mimeType: "image/jpeg", data }));
    let imageNote = images.length ? `포스터 이미지 ${images.length}장` : "";
    if (withImages && !images.length) {
      // 페이지 이미지를 읽을 수 없으면 지금 보이는 화면을 대신 보낸다
      const shot = await chrome.tabs.captureVisibleTab(tab.windowId, { format: "png" });
      images = [{ mimeType: "image/png", data: shot.split(",")[1] }];
      imageNote = "화면 캡처 1장";
    }

    showStatus("AI가 정리하는 중…");
    const prompt = await (await fetch(chrome.runtime.getURL("prompt.md"))).text();
    const header = [page.title, ...page.headings.filter((h) => h !== page.title)].join("\n");
    const message = MAGAMI.buildUserMessage(`${header}\n\n${page.text}`, {
      url: page.url,
      today: MAGAMI.todayKst(),
    });
    const raw = await callGemini({ apiKey, model, prompt, message, images });
    currentNotice = await MAGAMI.makeNotice(MAGAMI.parseResponse(raw), {
      url: page.url,
      channel: channelOf(page.url),
      source: "extension",
    });

    showStatus("");
    fillForm(currentNotice);
    refreshLinks();
    $("r-source").textContent =
      `본문 찾기: ${page.method === "readability" ? "Readability" : "페이지 구조"}` +
      (imageNote ? ` · ${imageNote}` : "") + ` · 모델: ${model}`;
    form.hidden = false;
  } catch (err) {
    showStatus(err.message || String(err), true);
  } finally {
    $("run").disabled = false;
  }
}

function download(name, data) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}

form.addEventListener("input", refreshLinks);
form.addEventListener("submit", async (e) => {
  e.preventDefault();
  if (!currentNotice) return;
  refreshLinks();
  await saveList(MAGAMI.upsertSaved(await loadSaved(), currentNotice));
  showStatus(currentNotice.deadline
    ? "내 마감 목록에 저장했습니다. 캘린더에도 넣으려면 '구글 캘린더에 추가'."
    : "저장했습니다. 마감일이 비어 있어 캘린더에는 추가할 수 없습니다.");
});
$("save-json").addEventListener("click", () => {
  if (!currentNotice) return;
  refreshLinks();
  download(`${currentNotice.id}.json`, currentNotice);
});
$("copy-json").addEventListener("click", async () => {
  if (!currentNotice) return;
  refreshLinks();
  await navigator.clipboard.writeText(JSON.stringify(currentNotice, null, 2));
  showStatus("JSON을 복사했습니다.");
});
$("run").addEventListener("click", run);
$("show-saved").addEventListener("click", async (e) => {
  e.preventDefault();
  form.hidden = true;
  showStatus("");
  $("saved").hidden = false;
  renderSaved();
});
$("back").addEventListener("click", () => { $("saved").hidden = true; });
$("export-all").addEventListener("click", async () => {
  download(`magami-saved-${MAGAMI.todayKst()}.json`, await loadSaved());
});
$("open-options").addEventListener("click", (e) => {
  e.preventDefault();
  chrome.runtime.openOptionsPage();
});

loadSaved().then(saveList);

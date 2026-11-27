// 팝업: 사용자가 버튼을 누를 때만 지금 탭 하나를 읽고 Gemini로 정리한다.
// 공지 목록을 돌거나 다른 페이지를 여는 기능은 없다 (docs/collection-policy.md).

const DEFAULT_MODEL = "gemini-2.5-flash";
const MAX_TEXT = 15000; // AI에 보낼 본문 최대 글자 수

const $ = (id) => document.getElementById(id);
let currentNotice = null;

function showStatus(message, isError = false) {
  const el = $("status");
  el.textContent = message;
  el.classList.toggle("error", isError);
  el.hidden = !message;
}

// 웹페이지 안에서 실행되는 함수. 제목·본문·주소만 돌려주고 아무것도 저장하지 않는다.
function readCurrentPage(maxText) {
  const selectors = [
    ".view-con", ".view_con", ".view_cont", ".bbs_view", ".board-view",
    ".board_view", "article", "#content", "main",
  ];
  let node = null;
  for (const s of selectors) {
    const found = document.querySelector(s);
    if (found && found.innerText.trim().length > 50) { node = found; break; }
  }
  const text = (node || document.body).innerText.replace(/\n{3,}/g, "\n\n").trim();
  return { title: document.title, url: location.href, text: text.slice(0, maxText) };
}

async function getSettings() {
  const { apiKey = "", model = "" } = await chrome.storage.local.get(["apiKey", "model"]);
  return { apiKey: apiKey.trim(), model: model.trim() || DEFAULT_MODEL };
}

async function callGemini({ apiKey, model, prompt, message, imageBase64 }) {
  const parts = [{ text: message }];
  if (imageBase64) parts.push({ inlineData: { mimeType: "image/png", data: imageBase64 } });
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

function render(notice) {
  $("result").hidden = false;
  $("not-notice").hidden = notice.is_notice;
  $("r-title").textContent = notice.title || "-";
  $("r-deadline").textContent = notice.deadline
    ? notice.deadline + (notice.deadline_time ? ` ${notice.deadline_time}` : "")
    : "확인 못 함";
  $("r-period").textContent = notice.apply_start || notice.apply_end
    ? `${notice.apply_start || "?"} ~ ${notice.apply_end || "?"}` : "-";
  $("r-target").textContent = notice.target || "-";
  $("r-how").textContent = notice.how_to_apply || "-";
  $("r-url").href = notice.url;

  const cal = $("add-calendar");
  const link = MAGAMI.calendarUrl(notice);
  if (link) {
    cal.href = link;
    cal.classList.remove("disabled");
  } else {
    cal.removeAttribute("href");
    cal.classList.add("disabled");
  }
}

async function run() {
  $("run").disabled = true;
  $("result").hidden = true;
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
    const [{ result: page }] = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: readCurrentPage,
      args: [MAX_TEXT],
    });

    let imageBase64 = null;
    if ($("with-capture").checked) {
      const dataUrl = await chrome.tabs.captureVisibleTab(tab.windowId, { format: "png" });
      imageBase64 = dataUrl.split(",")[1];
    }

    showStatus("AI가 정리하는 중…");
    const prompt = await (await fetch(chrome.runtime.getURL("prompt.md"))).text();
    const message = MAGAMI.buildUserMessage(`${page.title}\n\n${page.text}`, {
      url: page.url,
      today: MAGAMI.todayKst(),
    });
    const raw = await callGemini({ apiKey, model, prompt, message, imageBase64 });
    const fields = MAGAMI.parseResponse(raw);
    currentNotice = await MAGAMI.makeNotice(fields, {
      url: page.url,
      channel: channelOf(page.url),
      source: "extension",
    });
    showStatus("");
    render(currentNotice);
  } catch (err) {
    showStatus(err.message || String(err), true);
  } finally {
    $("run").disabled = false;
  }
}

function saveJson() {
  if (!currentNotice) return;
  const blob = new Blob([JSON.stringify(currentNotice, null, 2)], { type: "application/json" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `${currentNotice.id}.json`;
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}

async function copyJson() {
  if (!currentNotice) return;
  await navigator.clipboard.writeText(JSON.stringify(currentNotice, null, 2));
  showStatus("JSON을 복사했습니다.");
}

$("run").addEventListener("click", run);
$("save-json").addEventListener("click", saveJson);
$("copy-json").addEventListener("click", copyJson);
$("open-options").addEventListener("click", (e) => {
  e.preventDefault();
  chrome.runtime.openOptionsPage();
});
